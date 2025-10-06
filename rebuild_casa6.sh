#!/bin/bash

# Script to rebuild the CASA6 conda environment
# Usage: ./rebuild_casa6.sh [method]
# Methods: yaml (default), explicit, manual, pack

set -e

METHOD=${1:-yaml}
ENV_NAME="casa6"

echo "Rebuilding CASA6 environment using method: $METHOD"

case $METHOD in
    "yaml")
        echo "Creating environment from environment.yml..."
        conda env create -f environment.yml
        echo "Environment created successfully!"
        echo "Activate with: conda activate $ENV_NAME"
        ;;
    
    "explicit")
        echo "Creating environment from explicit package list..."
        conda create --name $ENV_NAME --file casa6_explicit.txt
        echo "Environment created successfully!"
        echo "Activate with: conda activate $ENV_NAME"
        ;;
    
    "manual")
        echo "Creating environment manually..."
        conda create -n $ENV_NAME python=3.11 -y
        conda activate $ENV_NAME
        echo "Installing conda packages..."
        conda install -c conda-forge casatasks casatools casacore casacpp astropy numpy scipy matplotlib pandas h5py -y
        echo "Installing pip packages..."
        pip install -r casa6_pip_requirements.txt
        echo "Environment created successfully!"
        echo "Activate with: conda activate $ENV_NAME"
        ;;
    
    "pack")
        echo "Using conda-pack method..."
        if [ ! -f "casa6_env.tar.gz" ]; then
            echo "Error: casa6_env.tar.gz not found!"
            echo "Please run 'conda pack -n casa6 -o casa6_env.tar.gz' on the original machine first."
            exit 1
        fi
        
        echo "Extracting packed environment..."
        mkdir -p ~/miniconda3/envs/$ENV_NAME
        tar -xzf casa6_env.tar.gz -C ~/miniconda3/envs/$ENV_NAME
        source ~/miniconda3/envs/$ENV_NAME/bin/activate
        conda-unpack
        echo "Environment unpacked successfully!"
        echo "Activate with: source ~/miniconda3/envs/$ENV_NAME/bin/activate"
        ;;
    
    *)
        echo "Unknown method: $METHOD"
        echo "Available methods: yaml, explicit, manual, pack"
        exit 1
        ;;
esac

echo ""
echo "To verify the installation, run:"
echo "conda activate $ENV_NAME"
echo "python -c \"import casatasks; print('CASA6 environment ready!')\""
