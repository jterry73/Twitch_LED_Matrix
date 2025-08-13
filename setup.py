import os
import subprocess
import sys
import shutil

def run_command(command):
    """Runs a command in the shell and checks for errors."""
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

def main():
    """Guides the user through the setup process."""
    print("--- Twitch LED Matrix Setup ---")

    # --- Step 1: Configure .env file ---
    if not os.path.exists('.env.example'):
        print("Error: .env.example file not found. Please make sure it exists.")
        sys.exit(1)

    shutil.copyfile('.env.example', '.env')
    print("1. Created .env file from .env.example.")

    print("\n2. Please enter your Twitch application credentials.")
    client_id = input("   Enter your TWITCH_CLIENT_ID: ")
    client_secret = input("   Enter your TWITCH_CLIENT_SECRET: ")
    username = input("   Enter your TWITCH_USERNAME: ")

    with open('.env', 'w') as f:
        f.write(f"TWITCH_CLIENT_ID={client_id}\n")
        f.write(f"TWITCH_CLIENT_SECRET={client_secret}\n")
        f.write(f"TWITCH_USERNAME={username}\n")
    print("   Successfully updated .env file.")

    # --- Step 2: Update docker-compose.yml ---
    print("\n3. Updating docker-compose.yml with your credentials...")
    try:
        with open('docker-compose.yml', 'r') as f:
            compose_content = f.read()
        
        compose_content = compose_content.replace('YOUR_CLIENT_ID_HERE', client_id)
        compose_content = compose_content.replace('YOUR_CLIENT_SECRET_HERE', client_secret)
        compose_content = compose_content.replace('YOUR_TWITCH_USERNAME', username)

        with open('docker-compose.yml', 'w') as f:
            f.write(compose_content)
        print("   Successfully updated docker-compose.yml.")
    except FileNotFoundError:
        print("   Warning: docker-compose.yml not found. Skipping update.")
        

    # --- Step 3 & 4: Create virtual environment and install requirements ---
    print("\n4. Creating Python virtual environment...")
    run_command("python3 -m venv .venv")
    
    # Determine the correct pip executable
    pip_executable = ".venv/bin/pip"
    if sys.platform == "win32":
        pip_executable = ".venv\\Scripts\\pip.exe"

    print("\n5. Installing required Python packages...")
    run_command(f"{pip_executable} install -r requirements.txt")

    # --- Step 5: Run authentication script ---
    print("\n6. Starting one-time user authentication...")
    
    python_executable = ".venv/bin/python"
    if sys.platform == "win32":
        python_executable = ".venv\\Scripts\\python.exe"
        
    run_command(f"{python_executable} authenticate.py")

    print("\n--- Setup Complete! ---")
    print("You can now build and run the application with the command:")
    print("docker compose up --build -d")

if __name__ == '__main__':
    main()
