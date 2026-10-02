# -*- coding: utf-8 -*-
"""Global constants and data organisation

"""
import os
# REPOSITORY DATA ORGANISATION
# -----------------------------------------------------------------------------/


# BIDS Path
BASE_BIDS_PATH = "/envau/work/meca/data/BaboFet_BIDS"
SOURCEDATA_BIDS_PATH = os.path.join(BASE_BIDS_PATH, "sourcedata")
DERIVATIVES_BIDS_PATH = os.path.join(BASE_BIDS_PATH, "derivatives")


######### NIOLON PATH
BASE_NIOLON_PATH = "/envau/work/meca/data/babofet_DB/2024_new_stuff"

# OTHERS PATH
SOFTS_PATH = os.path.join(BASE_NIOLON_PATH, "softs")
RECONS_FOLDER = os.path.join(BASE_NIOLON_PATH, "recons_folder")
FETAL_RESUS_ATLAS = os.path.join(BASE_NIOLON_PATH, "atlas_fetal_rhesus")

## LONGISEG PATH
LONGISEG_RAW_PATH = os.path.join(BASE_NIOLON_PATH, "LongiSeg_raw")
LONGISEG_RESULTS_PATH = os.path.join(BASE_NIOLON_PATH, "LongiSeg_trained_models")
LONGISEG_PREPROCESSED_PATH = os.path.join(BASE_NIOLON_PATH, "LongiSeg_preprocessed")

########################################################################################################################

######### MESOCENTRE PATH
BASE_PATH = "/scratch/lbaptiste/data"
CODE_PATH = "/scratch/lbaptiste/Babofet_T2w/"

# DATA PATH
DATA_PATH = os.path.join(BASE_PATH, "recons_folder")
TABLE_DATA_PATH = os.path.join(CODE_PATH, "table_data")

# LongiSeg path
LONGISEG_RAW_PATH_MESO = os.path.join(BASE_PATH, "LongiSeg_raw")
LONGISEG_RESULTS_PATH_MESO = os.path.join(BASE_PATH, "LongiSeg_results")
LONGISEG_PREPROCESSED_PATH_MESO = os.path.join(BASE_PATH, "LongiSeg_preprocessed")