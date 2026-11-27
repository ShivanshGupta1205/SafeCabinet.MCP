import mcp_types as t
from fastmcp import Context, FastMCP
from safecabinet.tools.drug_recalls import ANY_MANUFACTURER, check_drug_recalls as find_recalls

mcp = FastMCP("SafeCabinet")

NEW_PROTOCOL = "2026-07-28"
QUESTION_KEY = "manufacturer"


# ---------- helper functions ----------

def client_can_ask(ctx: Context) -> bool:
    """To check if the client can ask the user questions."""
    caps = ctx.session.client_capabilities
    return caps is not None and caps.elicitation is not None


def is_new_protocol(ctx: Context) -> bool:
    """check for the protocol version the client connects with"""
    request = ctx.request_context
    return request is not None and request.protocol_version == NEW_PROTOCOL


def already_asked(ctx: Context) -> bool:
    """New protocol only: True on the second call, when the client brings back an answer."""
    responses = ctx.input_responses
    return responses is not None and QUESTION_KEY in responses


def picked_manufacturer(ctx: Context) -> str | None:
    """New protocol only: the manufacturer the user picked, or None if they declined/cancelled."""
    responses = ctx.input_responses
    reply = responses.get(QUESTION_KEY) if responses else None
    if not isinstance(reply, t.ElicitResult) or reply.action != "accept" or not reply.content:
        return None
    value = reply.content.get(QUESTION_KEY)
    return value if isinstance(value, str) else None


def manufacturer_question(question: str, options: list[str]) -> t.InputRequiredResult:
    """New protocol only: the "please ask the user this, then call me again" answer."""
    form = t.ElicitRequestFormParams(
        message=question,
        requested_schema={
            "type": "object",
            "properties": {QUESTION_KEY: {"type": "string", "title": "Manufacturer", "enum": options}},
            "required": [QUESTION_KEY],
        },
    )
    return t.InputRequiredResult(input_requests={QUESTION_KEY: t.ElicitRequest(params=form)})


def search_with_pick(pick: str, product: str, lot_number: str | None, include_past: bool) -> dict:
    """Re-run the search with the user's answer. "Any manufacturer" means search every firm."""
    if pick == ANY_MANUFACTURER:
        return find_recalls(product, lot_number=lot_number, include_past=include_past, all_manufacturers=True)
    return find_recalls(product, manufacturer=pick, lot_number=lot_number, include_past=include_past)



# ---------- MCP Tool ----------

@mcp.tool()
async def check_drug_recalls(
    ctx: Context,
    product: str,
    manufacturer: str | None = None,
    lot_number: str | None = None,
    include_past: bool = False,
    all_manufacturers: bool = False,
) -> dict | t.InputRequiredResult:
    """Check whether a medicine has FDA recalls. Use for questions like "Is my Tylenol recalled?".

    Searches FDA drug recall records (openFDA) by product name. By default it returns only
    recalls that are still ongoing or started in the last 6 months, at most 10, active first.
    If several companies have recalls for the product, the tool asks the user which one.

    The data names the company that recalled the product and the US states it was shipped to.
    It cannot say which store or pharmacy sold it, so it cannot answer "recalls at my CVS"
    except by product and company. Always pass on the result's data_limitations and disclaimer.
    "No recall found" never means the product is safe.

    Args:
        product: Medicine name as the user said it, brand or generic (e.g. "tylenol", "metformin").
        manufacturer: Company on the label. Only set it if the user said it or read it from the
            bottle. Never guess.
        lot_number: Lot number from the label, if the user gave one. It is not matched
            automatically; compare it with each result's code_info.
        include_past: True only when the user asks whether it was EVER recalled, or asks about
            old or finished recalls.
        all_manufacturers: True when the user wants every company ("any brand", "all
            manufacturers"). Skips the which-manufacturer question.
    """
    # New protocol, second call: the user's answer from the picker arrives here.
    if manufacturer is None and not all_manufacturers:
        pick = picked_manufacturer(ctx)
        if pick is not None:
            return search_with_pick(pick, product, lot_number, include_past)

    result = find_recalls(product, manufacturer, lot_number, include_past, all_manufacturers)
    clarification = result["needs_clarification"]

    # Nothing to ask, or the client can't show questions -> Branch A (fallback, LLM asks in chat).
    if clarification is None or not client_can_ask(ctx):
        return result

    # Branch B: new protocol. Ask by returning a question; the client calls us again with the answer.
    if is_new_protocol(ctx):
        if already_asked(ctx):  # we asked, user declined -> don't ask again (that would loop forever)
            return result
        return manufacturer_question(clarification["question"], clarification["options"])

    # Branch C: older protocol. Ask and wait right here.
    answer = await ctx.elicit(clarification["question"], clarification["options"])
    if answer.action == "accept":
        return search_with_pick(answer.data, product, lot_number, include_past)
    return result  # declined or cancelled -> fallback answer


if __name__ == "__main__":
    mcp.run()
