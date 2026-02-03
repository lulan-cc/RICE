# RICE: Harnessing LLMs and Historical Issues to Discover Internal Rust Compiler Errors

## Project Background

RICE is an LLM-assisted testing framework for the Rust compiler designed to uncover internal compiler errors. It learns buggy code patterns from historical ICE issues and applies them to broader code contexts to discover more compiler crash paths.

## Project Structure
The directory structure of the BridgeRouter project is as follows:
```
RICE/  
|—— comparison/       # Comparative experimental data
|—— dataset/          # Historical ICE issue reports
|—— src/              # Code of RICE
|—— zero_days/        # 0day ices  
|—— .env.exmaple      # Environmental variable config
└── README.md         # This documentation  
```

## Environment Setup
Before using this tool, please ensure that the following development tools are installed on your computer:
- python>=3.8
- rustc>=1.82

You have to install all the libraries listed in requirements.txt
```
pip install -r requirements.txt
```

## Usage
1. Please copy `.env.example` to `.env` and configure the deepseek API key, base URL, and model name.
2. Navigate to the `src` directory and run `main.py`, while providing the known ICE issue report you wish to target.
```
cd src
python3 main.py ../dataset/history_ices/issue_128249.md
```
3. The tool's runtime logs and the code that triggers ICEs will be saved in the `output` directory.

During execution, this tool will locally build a Rust compiler for a specific commit. For details, please refer to: [rustc quick start](https://rustc-dev-guide.rust-lang.org/building/quickstart.html)