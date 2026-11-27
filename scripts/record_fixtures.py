import json
from safecabinet.openfda.client import get

data = [
    {
        "name": "Tylenol",
        "manufacturer": None
    },
    {
        "name": "Metformin",
        "manufacturer": "Teva Pharmaceuticals USA"
    },
    {
        "name": "Atorvastatin",
        "manufacturer": None
    },
    {
        "name": "Lisinopril",
        "manufacturer": None
    }
]

for drugInfo in data:
    drug = drugInfo["name"]
    manufacturer = drugInfo["manufacturer"]
    try:
        if manufacturer:
            response = get("drug/enforcement", f'product_description:"{drug}" AND recalling_firm:"{manufacturer}"', limit=10)
        else:
            response = get("drug/enforcement", f'product_description:"{drug}"', limit=10)
    except Exception as e:
        print(f"Error fetching data for {drug}: {e}")
        continue
    
    slug = f"{drug}_{manufacturer.split()[0]}" if manufacturer else drug
    file_name = f"tests/fixtures/drug_enforcement_{slug.lower()}.json"
    with open(file_name, "w") as f:
        json.dump(response, f, indent=4)
        print(f"Saved data for {drug} to {file_name}")
    




