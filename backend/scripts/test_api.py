import requests
import json

def test_search():
    url = "http://localhost:8000/api/v1/search/text"
    payload = {
        "query": "dense urban settlement or buildings",
        "top_k": 2
    }
    print(f"[*] Testing POST {url} with {payload}")
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
    print("-" * 80)

def test_change():
    url = "http://localhost:8000/api/v1/analyze/change"
    payload = {
        "col_off": 4500,
        "row_off": 4500,
        "width": 512,
        "height": 512,
        "force": True
    }
    print(f"[*] Testing POST {url} with {payload}")
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    # We truncate features to save screen space
    resp_data = response.json()
    if 'detected_features' in resp_data and 'features' in resp_data['detected_features']:
        features = resp_data['detected_features']['features']
        print(f"-> Detected features count: {len(features)}")
        # Remove massive geometry to print cleanly
        if features:
            resp_data['detected_features']['features'] = [f"Truncated {len(features)} features"]
    
    print(json.dumps(resp_data, indent=2))
    print("-" * 80)

if __name__ == "__main__":
    test_search()
    test_change()
