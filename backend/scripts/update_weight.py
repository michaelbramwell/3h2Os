import sys
import httpx
import asyncio

API_URL = "http://localhost:8000/api"

async def update_weight(weight: float):
    url = f"{API_URL}/context/weight"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"weight": weight})
            if response.status_code == 200:
                print(f"Successfully updated weight to {weight}kg via API.")
                print(response.json())
            else:
                print(f"Failed to update weight. Status: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"Error connecting to API: {e}")
        print(f"Ensure the server is running at {API_URL}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/update_weight.py <weight_in_kg>")
        sys.exit(1)
    
    try:
        w_val = float(sys.argv[1])
        asyncio.run(update_weight(w_val))
    except ValueError:
        print("Error: Weight must be a number.")
        sys.exit(1)
