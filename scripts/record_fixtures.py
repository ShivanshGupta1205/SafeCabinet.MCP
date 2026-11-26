import json
from safecabinet.openfda.client import get

drugs = ["tylenol", "metformin", "atorvastatin", "lisinopril"]

for drug in drugs:
    try:
        response = get("drug/enforcement", f'product_description:"{drug}"', limit=10)
    except Exception as e:
        print(f"Error fetching data for {drug}: {e}")
        continue
    
    with open(f"tests/fixtures/drug_enforcement_{drug}.json", "w") as f:
        json.dump(response, f, indent=4)
        print(f"Saved data for {drug} to tests/fixtures/drug_enforcement_{drug}.json")
    




