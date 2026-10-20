# 🪟 Step-by-Step Guide: Running CompilerX in VS Code on Windows 11

This guide walks you through setting up, running, testing, and demonstrating **CompilerX** inside **Visual Studio Code (VS Code)** on **Windows 11**.

## 1. Prerequisites Check

1. **Install Python (3.10, 3.11, or 3.12)**:
   - Download from [python.org/downloads/windows](https://www.python.org/downloads/windows/).
   - **Important**: During installation, check the box **"Add python.exe to PATH"** at the bottom of the installer window.
2. **Install Visual Studio Code**:
   - Download from [code.visualstudio.com](https://code.visualstudio.com/).
   - Open VS Code, click the **Extensions** icon on the left sidebar (`Ctrl+Shift+X`), search for **Python** (by Microsoft), and click **Install**.

## 2. Extract and Open the Project in VS Code

1. Locate the downloaded `CompilerX.zip` file in **File Explorer**.
2. Right-click `CompilerX.zip` and select **Extract All...** to a clean folder (for example, `C:\Projects\CompilerX`).
3. Open **VS Code**.
4. Click **File -> Open Folder...** (`Ctrl+K Ctrl+O`) and select the extracted `CompilerX` folder (the folder that directly contains `app.py`, `lexer.py`, `requirements.txt`, etc.).
5. If prompted *"Do you trust the authors of the files in this folder?"*, click **Yes, I trust the authors**.

## 3. Open the Integrated Terminal & Create a Virtual Environment

1. Inside VS Code, open the integrated terminal by pressing `` Ctrl+` `` (Control + backtick) or clicking **Terminal -> New Terminal** from the top menu bar.
2. Verify Python is accessible by running:
   ```powershell
   python --version
   ```
3. Create an isolated Python virtual environment named `venv`:
   ```powershell
   python -m venv venv
   ```
4. Activate the virtual environment in Windows PowerShell:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   > **Troubleshooting PowerShell Execution Policy Error**:
   > If Windows 11 displays an error saying *"running scripts is disabled on this system (PSSecurityException)"*, run this command once in the same terminal to allow local scripts for your user account:
   > ```powershell
   > Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   > ```
   > Then run `.\venv\Scripts\Activate.ps1` again. You should now see `(venv)` in green at the start of your terminal prompt.

5. Select the Virtual Environment Interpreter in VS Code:
   - Press `Ctrl+Shift+P` to open the Command Palette.
   - Type **Python: Select Interpreter** and press `Enter`.
   - Choose the option labeled `.\venv\Scripts\python.exe`.

## 4. Install Dependencies

With `(venv)` active in the terminal, install Streamlit:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Run the Automated Unit Tests

Before launching the UI, verify that all 7 compiler phases pass automated testing:
```powershell
python -m unittest discover -s tests -v
```
You will see each test execute (`TestPhase1Lexer`, `TestPhase2Parser`, `TestPhase3SemanticAnalyzer`, `TestPhase4And5TACAndOptimization`, `TestPhase6And7TargetGenAndInterpreter`, `TestStreamlitAppSmoke`) and end with `OK`.

## 6. Launch the Streamlit Web Application

Start the interactive CompilerX web app from the VS Code terminal:
```powershell
streamlit run app.py
```
- Your default browser (Edge or Chrome) will automatically open to **`http://localhost:8501`**.
- If it does not open automatically, `Ctrl+Click` the `http://localhost:8501` link shown in the terminal.
- To stop the server when finished, click inside the VS Code terminal and press `Ctrl+C`.

## 7. Optional: Run CompilerX in CLI Mode Inside VS Code

To test programs directly in the VS Code terminal without opening a browser:
```powershell
# Run the default arithmetic & if/else example
python app.py --cli

# Run the factorial & while-loop example
python app.py --cli examples\03_while_loop_factorial.cx
```
