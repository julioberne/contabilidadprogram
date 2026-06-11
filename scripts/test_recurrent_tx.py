import requests
import json

payload = {
  "portfolio_name": "MI EMPRESA",
  "pocket_id": None,
  "type": "GASTO",
  "amount": 100000,
  "concept": "Test Synthetic Data",
  "payment_method": "EFECTIVO",
  "category": "1000 - General",
  "third_party": {
    "identification_type": "NIT",
    "identification_number": "123456789",
    "name": "Synthetic Inc",
    "email": "test@synth.com",
    "phone": "5551234",
    "website": ""
  },
  "transaction_date": "2026-06-04",
  "apply_iva": False,
  "apply_gmf": False,
  "account_id": 1,
  "dest_account_id": None,
  "trm": 1.0,
  "transaction_currency": "COP",
  "is_recurring": True,
  "recurrence_interval": "MENSUAL",
  "recurrence_days": 30,
  "recurrence_max_reps": 12,
  "recurrence_start_date": "2026-06-04",
  "recurrence_end_date": "2027-06-04",
  "custom_taxes": [],
  "cxc_cxp": None,
  "asset": None
}

try:
    response = requests.post("http://localhost:8000/api/transactions", json=payload)
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())
except Exception as e:
    print("Exception:", e)
