import requests
import json
import time

BASE_URL = 'http://127.0.0.1:8000'

def login(email, password):
    url = f"{BASE_URL}/api/auth/login/"
    response = requests.post(url, json={"email": email, "password": password})
    if response.status_code == 200:
        return response.json()['access']
    else:
        print(f"Login failed for {email}: {response.text}")
        return None

print("=== Starting End-to-End API Test for Engagements ===")

# 1. Login as Pathfinder
print("\n1. Logging in as Pathfinder...")
pathfinder_token = login("volunteer@test.com", "password123!")
if not pathfinder_token:
    exit(1)
headers_pathfinder = {"Authorization": f"Bearer {pathfinder_token}"}

# 2. Get engagements for pathfinder
print("\n2. Fetching Pathfinder's Engagements...")
resp = requests.get(f"{BASE_URL}/api/engagements/me/", headers=headers_pathfinder)
engagements = resp.json()
if not engagements:
    print("No engagements found! Please ensure seed data was created properly.")
    exit(1)

engagement = engagements[0]
engagement_id = engagement['id']
print(f"Found Engagement ID: {engagement_id} for opportunity {engagement['opportunity']}")

# 3. Add a Task
print("\n3. Pathfinder logging a task...")
task_payload = {
    "engagement": engagement_id,
    "date": "2026-09-10",
    "description": "Led the beach cleanup successfully."
}
resp = requests.post(f"{BASE_URL}/api/engagements/tasks/", json=task_payload, headers=headers_pathfinder)
if resp.status_code in [201, 200]:
    print("Task successfully added!")
else:
    print(f"Failed to add task: {resp.text}")

# 4. Request Attestation
print("\n4. Pathfinder requesting attestation...")
resp = requests.post(f"{BASE_URL}/api/engagements/{engagement_id}/request_attestation/", headers=headers_pathfinder)
if resp.status_code == 200:
    print("Attestation successfully requested!")
else:
    print(f"Failed to request attestation: {resp.text}")

# 5. Login as Enabler
print("\n5. Logging in as Enabler...")
enabler_token = login("enabler@test.com", "password123!")
if not enabler_token:
    exit(1)
headers_enabler = {"Authorization": f"Bearer {enabler_token}"}

# 6. Enabler fetches pending attestations
print("\n6. Enabler fetching pending attestations...")
resp = requests.get(f"{BASE_URL}/api/engagements/pending_attestations/", headers=headers_enabler)
pending = resp.json()
print(f"Found {len(pending)} pending attestations.")

# 7. Enabler attests the record
print("\n7. Enabler attesting the record...")
attest_payload = {
    "endorsement_note": "Great work leading the beach cleanup!"
}
resp = requests.post(f"{BASE_URL}/api/engagements/{engagement_id}/attest/", json=attest_payload, headers=headers_enabler)
if resp.status_code == 200:
    print("Record successfully attested!")
else:
    print(f"Failed to attest record: {resp.text}")

# 8. Pathfinder fetches the generated certificate
print("\n8. Pathfinder fetching digital certificate...")
resp = requests.get(f"{BASE_URL}/api/engagements/{engagement_id}/certificate/", headers=headers_pathfinder)
if resp.status_code == 200:
    cert = resp.json()
    cert_id = cert['certificate_id']
    pdf_url = cert['pdf_file']
    print(f"Certificate successfully generated! ID: {cert_id}")
    print(f"PDF Download URL: {pdf_url}")
else:
    print(f"Failed to fetch certificate: {resp.text}")
    exit(1)

# 9. Public Verification API (No Auth)
print(f"\n9. Public User verifying the certificate at /api/engagements/verify/{cert_id}/ ...")
resp = requests.get(f"{BASE_URL}/api/engagements/verify/{cert_id}/")
if resp.status_code == 200:
    public_data = resp.json()
    print("--- Public Verification Data ---")
    print(f"Volunteer: {public_data['volunteer_name']}")
    print(f"Opportunity: {public_data['opportunity_title']}")
    print(f"Organization: {public_data['organization_name']}")
    print(f"Endorsement: {public_data['endorsement_note']}")
    print(f"Status: {public_data['status']}")
    print("--------------------------------")
else:
    print(f"Failed public verification: {resp.text}")

print("\n=== End-to-End API Test Completed Successfully! ===")
