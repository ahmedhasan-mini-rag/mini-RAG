# mini-RAG

This a full RAG(Retrieval Augmented Generation) app for question answering

## Requirements

- Python >= 3.12 
- uv

## Setup Steps

1) #### Install and download uv from [here](https://docs.astral.sh/uv/getting-started/installation/)

2) #### Move to you preferred directory and clone the repo:
```bash
git clone https://github.com/AhmeDHasan-110/mini-RAG.git
cd mini-RAG
```

3) #### Setup a new environment by running:
```bash
# make sure you are in mini-RAG directory
uv sync
```
This command mainly does the follwoing:
- creates a new virtual environment.
- installs all dependencies listed in `pyproject.toml`.
- installs the needed python version if not found.
  
4) #### Setup environment configuration:
```bash
cp .env.example .env
```
Now load the `.env` file with your values.
