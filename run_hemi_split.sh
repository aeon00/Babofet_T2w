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
if [ "$#" -ne 2 ]; then
    echo "Error: Missing arguments."
    echo "Usage: sbatch $0 <subject_id> <session_id>"
    echo "Example: sbatch $0 sub-Borgne ses-01"
    exit 1
fi

SUBJECT=$1
SESSION=$2

echo "Starting Hemisphere Splitting for subject: ${SUBJECT} session: ${SESSION}"

module purge
module load all
module load FSL
module load ANTS

# Hemisphere Splitting and Registration
echo "Running 02_hemi_split.py for ${SUBJECT} ${SESSION}"
python extraction_module/02_hemi_split.py --subject "${SUBJECT}" --session "${SESSION}"
echo "------------------------------------------------------------------------------"
echo "Hemisphere splitting finished."
