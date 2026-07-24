import requests

def ask_qwen(prompt: str) -> str:
    response = requests.post(
        "https://owner12345-qwen-api.hf.space/api/predict",
        json={"data": [prompt, 512, 0.85]},
        timeout=60
    )
    
    if response.status_code == 200:
        return response.json()["data"][0]
    else:
        return f"Ошибка: {response.status_code}"