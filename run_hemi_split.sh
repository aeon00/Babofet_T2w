#!/bin/bash
#SBATCH -J hemi_split
#SBATCH -p interactive
#SBATCH --mem-per-cpu=48G
#SBATCH --time=12:00:00
#SBATCH -N 1
#SBATCH -o logs/hemi_split_%j.out
#SBATCH -e logs/hemi_split_%j.err
set -e

# Check for arguments
if [ "$#" -ne 3 ]; then
    echo "Error: Missing arguments."
    echo "Usage: sbatch $0 <subject_id> <session_id> <output_root>"
    echo "Example: sbatch $0 sub-Borgne ses-01 /envau/work/meca/users/dienye.h/python_files/Babofet/sub-Borgne/sub-Borgne-seg"
    exit 1
fi

SUBJECT=$1
SESSION=$2
OUTPUT_ROOT=$3

echo "Starting Hemisphere Splitting for subject: ${SUBJECT} session: ${SESSION}"
echo "Output root: ${OUTPUT_ROOT}"

module purge
module load all
module load FSL
module load ANTS

# Activate conda the same way as your working scripts on this cluster
source ~/.bashrc
conda activate babofet

# FSL and ANTS modules put their own python on PATH, which shadows the conda one.
# Call the conda env's python explicitly so antspyx/numpy/pandas are guaranteed.
echo "CONDA_PREFIX = ${CONDA_PREFIX}"

# Hemisphere Splitting and Registration
echo "Running 02_hemi_split.py for ${SUBJECT} ${SESSION}"
"${CONDA_PREFIX}/bin/python" extraction_module/02_hemi_split.py \
    --subject "${SUBJECT}" \
    --session "${SESSION}" \
    --output "${OUTPUT_ROOT}"
echo "------------------------------------------------------------------------------"
echo "Hemisphere splitting finished."