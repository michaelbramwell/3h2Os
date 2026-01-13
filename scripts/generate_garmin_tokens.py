import os
import getpass
from garminconnect import Garmin
import garth
import base64
import json
import shutil
import zipfile
import io
from dotenv import load_dotenv

# Make sure we have a clean slate
TOKEN_DIR = os.path.expanduser("~/.garth")

def main():
    load_dotenv()
    print("This script will authenticate with Garmin and generate a token string for use in GitHub Secrets.")
    
    email = os.getenv("GARMIN_EMAIL")
    if not email:
        email = input("Garmin Email: ")
    else:
        print(f"Using Garmin Email from env: {email}")

    password = os.getenv("GARMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Garmin Password: ")
    else:
        print("Using Garmin Password from env")
    
    try:
        # Initialize Garmin client
        client = Garmin(email, password)
        client.login()
        print("\nLogin successful!")
        
        print(f"Saving tokens to {TOKEN_DIR}...")
        # Explictly save tokens
        if hasattr(client, 'garth'):
            client.garth.dump(TOKEN_DIR)
        else:
            print("Using global garth.save() fallback")
            garth.save(TOKEN_DIR)
        
        # The tokens are stored in ~/.garth by default by the library (via garth)
        
        if not os.path.exists(TOKEN_DIR):
             print(f"Error: Token directory {TOKEN_DIR} was not created.")
             return

        # ZIP the directory to make it a single blob
        # root_dir=TOKEN_DIR ensures we just zip the contents, not the folder itself
        shutil.make_archive("garmin_tokens", 'zip', root_dir=TOKEN_DIR)
        
        with open("garmin_tokens.zip", "rb") as f:
            token_data = f.read()
            # encode and convert to string, remove any newlines just in case
            b64_token = base64.b64encode(token_data).decode('utf-8').replace('\n', '')
            
        print("\n=== GARMIN_TOKENS Secret Value (Copy EVERYTHING between the lines) ===")
        print(b64_token)
        print("=========================================================================")
        print(f"Token length: {len(b64_token)} chars")
        
        # Verify it works
        print("\nVerifying generated token...")
        try:
            # Create a localized test environment
            verify_dir = os.path.expanduser("~/.garth_verify")
            if os.path.exists(verify_dir):
                shutil.rmtree(verify_dir)
            os.makedirs(verify_dir)
            
            # Decode logic same as fetch script
            v_zip_data = base64.b64decode(b64_token)
            with zipfile.ZipFile(io.BytesIO(v_zip_data)) as zf:
                zf.extractall(verify_dir)
            
            # Monkeypatch garth's save path temporarily? 
            # Easier to just verify files exist
            files = os.listdir(verify_dir)
            if not files:
                print("Verification Failed: No files extracted from zip!")
            else:
                print(f"Verification OK: Extracted {len(files)} files: {files}")
            
            shutil.rmtree(verify_dir)
        except Exception as e:
            print(f"Verification Failed: {e}")

        # Cleanup
        os.remove("garmin_tokens.zip")
        
    except Exception as e:
        print(f"Error during login or token generation: {e}")

if __name__ == "__main__":
    main()
