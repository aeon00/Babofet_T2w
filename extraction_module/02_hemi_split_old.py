import argparse
import subprocess
import os
import sys
import tempfile
import ants as ants
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.abspath(os.curdir))
import configuration as cfg


def get_gestational_info(female_name, session_id, tsv_file):
    # Atlas available timepoints
    atlas_timepoints = [85, 97, 110, 122, 135, 147, 155]

    df = pd.read_csv(tsv_file, sep='\t')

    session_data = df[df['session_id'].str.strip() == session_id]

    if session_data.empty:
        print(f"Error: Session {session_id} not found for {female_name}.")
        return None

    gestational_age = session_data['gestational_age'].values[0]

    adequate_atlas = min(atlas_timepoints, key=lambda x: abs(x - gestational_age))

    return gestational_age, adequate_atlas




def fsl_register_single(atlas_file, base_subj_path, subject, session, output_dir):
    # SUBJECT_SESSION_rec-niftymic_desc-brainbg_T2w.nii.gz
    reference = os.path.join(base_subj_path, f"{subject}_{session}_rec-niftymic_desc-brainbg_T2w.nii.gz")

    # SUBJECT_SESSION_rec-niftymic_desc-brain_mask.nii.gz
    reference_mask = os.path.join(base_subj_path, f"{subject}_{session}_rec-niftymic_desc-brain_mask.nii.gz")

    # Brain-masked T2w is a temporary product now: written into the scratch dir
    # (output_dir) instead of the niftymic folder, so no input folder is touched.
    new_reference = os.path.join(output_dir, f"{subject}_{session}_rec-niftymic_desc-brain_T2w.nii.gz")

    subprocess.run(
        ["fslmaths", reference, "-mul", reference_mask, new_reference],
        check=True,
    )

    moving_file = os.path.basename(atlas_file)
    moving_name = moving_file.replace(".nii.gz", "_affine.nii.gz")
    moving_mat = moving_file.replace(".nii.gz", "_affine.mat")

    out_nii = os.path.join(output_dir, moving_name)
    out_mat = os.path.join(output_dir, moving_mat)

    if os.path.exists(out_nii):
        print(f"\t\t\t{moving_name} already exists, skipping...")
        return

    print(f"\t\tStarting registration with FLIRT for {moving_file}")
    subprocess.run(
        [
            "flirt",
            "-in", atlas_file,
            "-ref", new_reference,
            "-out", out_nii,
            "-omat", out_mat,
            "-dof", "12",
            "-cost", "mutualinfo",
            "-searchrx", "-180", "180",
            "-searchry", "-180", "180",
            "-searchrz", "-180", "180",
            "-interp", "spline"
        ],
        check=True,
    )
    print("\t\tFLIRT registration done")


def convert_fsl2ants(input_atlas_registered, best_atlas, subject, session, base_subj_path):
    """
    tools/c3d_affine_tool \
        -ref ${REFERENCE} \
        -src ${MOVING} \
        "$OUTPUT_DIR/affine.mat" \
        -fsl2ras \
        -oitk "$OUTPUT_DIR/affine.txt"
    """

    best_atlas_name = os.path.basename(best_atlas)
    affine_file = os.path.join(input_atlas_registered, best_atlas_name.replace(".nii.gz", "_affine.mat"))
    oitk = os.path.join(input_atlas_registered, best_atlas_name.replace(".nii.gz", "_affine.txt"))

    tools_c3d_affine_tool_path = os.path.join(cfg.SOFTS_PATH, "c3d_affine_tool")
    subprocess.run(
        [
            tools_c3d_affine_tool_path,
            "-ref", os.path.join(base_subj_path, f"{subject}_{session}_rec-niftymic_desc-brain_mask.nii.gz"),
            "-src", best_atlas,
            affine_file,
            "-fsl2ras",
            "-oitk", oitk
        ]
    )

    print("\t\tAffine conversion done")


def ants_nonlinear_registration(input_atlas_registered, base_subj_path, best_atlas, best_atlas_mask, subject, session):
    # The brain-masked T2w lives in the scratch dir (input_atlas_registered),
    # matching where fsl_register_single wrote it.
    ref = os.path.join(input_atlas_registered, f"{subject}_{session}_rec-niftymic_desc-brain_T2w.nii.gz")
    ref_mask = os.path.join(base_subj_path, f"{subject}_{session}_rec-niftymic_desc-brain_mask.nii.gz")

    ants_prefix = f"{input_atlas_registered}/ants_"
    ants_warped_image = f"{subject}_{session}_warped_IMAGE.nii.gz"

    best_atlas_name = os.path.basename(best_atlas)
    initial_moving_transform = os.path.join(input_atlas_registered, best_atlas_name.replace(".nii.gz", "_affine.txt"))
    full_ouput_name = f"{ants_prefix}{ants_warped_image}"

    if os.path.exists(full_ouput_name):
        print(f"\t\t{full_ouput_name} already exists, skipping...")
    else:
        subprocess.run(
        [
            "antsRegistration",
            "--verbose", "1",
            "--dimensionality", "3",
            "--float", "0",
            "--output", f"[{ants_prefix},{full_ouput_name}]",
            "--interpolation", "BSpline",
            "--use-histogram-matching", "1",
            "--winsorize-image-intensities", "[0.001,0.999]",
            "--initial-moving-transform", initial_moving_transform,
            "--transform", "SyN[0.1,3,0]",
            "--metric", f"Mattes[{ref},{best_atlas}, 1, 64]",
            "--convergence", "[200x200x200x100x100x100, 1e-6, 10]",
            "--shrink-factors", "4x4x2x2x1x1",
            "--smoothing-sigmas", "6x5x4x2x1x0",
            "--masks", f"[{ref_mask},{best_atlas_mask}]",
        ],
            check=True,
        )


def apply_ants_transformations(input_atlas_registered, base_subj_path, moving_seg, affine_file, subject, session):
    ref_mask = os.path.join(base_subj_path, f"{subject}_{session}_rec-niftymic_desc-brain_mask.nii.gz")

    output = os.path.join(input_atlas_registered, "warped_regionals.nii.gz")
    transform_file = os.path.join(input_atlas_registered, "ants_1Warp.nii.gz")

    subprocess.run(
        [
            "antsApplyTransforms",
            "--dimensionality", "3",
            "--input", f"{moving_seg}",
            "--reference-image", f"{ref_mask}",
            "--output", output,
            "--transform", transform_file,
            "--transform", affine_file,
            "--interpolation", "GenericLabel",
        ],
        check=True,
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Split brain segmentation into hemispheres and register to atlas.")
    parser.add_argument("--subject", type=str, help="Subject ID to process (e.g., sub-Borgne)")
    parser.add_argument("--session", required=True, help="Session ID (e.g., ses-01)")
    args = parser.parse_args()

    input_volume_path = os.path.join(cfg.DERIVATIVES_BIDS_PATH, "niftymic")
    input_seg_path = os.path.join(cfg.DERIVATIVES_BIDS_PATH, "longiseg")
    intermediate_path = os.path.join(cfg.DERIVATIVES_BIDS_PATH, "intermediate", "surf-slam")

    atlas_path = os.path.join(cfg.BASE_NIOLON_PATH, "atlas_fetal_rhesus_v2")
    volumes_atlas_path = os.path.join(atlas_path, "Volumes")

    segmentation_atlas_path = os.path.join(intermediate_path, "structures_dilated")
    if not os.path.exists(segmentation_atlas_path):
        print(f"Error ! {segmentation_atlas_path} does not exist. Run the previous script before")
        exit()

    subject = args.subject
    session = args.session

    print(f"Processing {subject} {session}")
    subject_path = os.path.join(input_seg_path, subject)

    # Folder holding the input segmentation. The split hemispheres are the ONLY
    # file written back here; it is the sole permanent output of this script.
    session_path = os.path.join(subject_path, session, "anat")


    # SUBJECT_SESSION_desc-longiseg_dseg.nii.gz

    t2_subj_seg = os.path.join(session_path, f"{subject}_{session}_desc-longiseg_dseg.nii.gz")
    try:
        fixed_seg = ants.image_read(t2_subj_seg)
    except ValueError:
        t2_subj_seg = os.path.join(session_path, f"{subject}_{session}_desc-longiseg_dseg_gt.nii.gz")
        fixed_seg = ants.image_read(t2_subj_seg)

    # SUBJECT_SESSION_rec-niftymic_desc-brain_T2w.nii.gz
    recons_volumes_folder = os.path.join(input_volume_path, subject, session, "anat")

    # Final output: written to the same folder as the input segmentation (session_path).
    file_seg_out = os.path.join(session_path, f"{subject}_{session}_hemi.nii.gz")
    if os.path.exists(file_seg_out):
        print(f"\t\tSegmentation for {subject} {session} already exists, skipping...")
        exit(0)

    # All registration intermediates (FLIRT affines, ANTs warps, warped_regionals,
    # brain-masked T2w) go into a temporary directory that is deleted automatically
    # when the block exits, whether it succeeds or errors. Only file_seg_out survives.
    # dir=intermediate_path keeps scratch on the data filesystem (not a small /tmp).
    with tempfile.TemporaryDirectory(prefix=f"{subject}_{session}_hemi_", dir=intermediate_path) as scratch_dir:

        tsv_file = os.path.join(cfg.SOURCEDATA_BIDS_PATH, "raw", subject, f"{subject}_sessions.tsv")
        subject_ga, atlas_ga = get_gestational_info(subject, session, tsv_file)
        print(f"\t\tGestational age: {subject_ga} → using atlas G{atlas_ga}")

        atlas_filename = f"ONPRC_G{atlas_ga}_Norm.nii.gz"
        best_atlas_path = os.path.join(volumes_atlas_path, atlas_filename)

        fsl_register_single(
            atlas_file=best_atlas_path,
            base_subj_path=recons_volumes_folder,
            subject=subject,
            session=session,
            output_dir=scratch_dir
        )

        # best_atlas is the registered output filename, used by downstream .replace() calls
        best_atlas = atlas_filename.replace(".nii.gz", "_affine.nii.gz")
        print(f"\t\tSelected atlas: {best_atlas}")

        convert_fsl2ants(
            input_atlas_registered=scratch_dir,
            best_atlas=best_atlas_path,
            subject=subject,
            session=session,
            base_subj_path=recons_volumes_folder
        )

        mask_best_atlas = os.path.join(segmentation_atlas_path, best_atlas.replace("Norm_affine", "NFseg_bm"))

        ants_nonlinear_registration(
            input_atlas_registered=scratch_dir,
            base_subj_path=recons_volumes_folder,
            best_atlas=best_atlas_path,
            best_atlas_mask=mask_best_atlas,
            subject=subject,
            session=session
        )

        subj_seg = os.path.join(segmentation_atlas_path, best_atlas.replace("Norm_affine", "structures_dilated"))

        affine_file = os.path.join(scratch_dir, best_atlas.replace("_affine.nii.gz", "_affine.txt"))

        apply_ants_transformations(
            input_atlas_registered=scratch_dir,
            base_subj_path=recons_volumes_folder,
            moving_seg=subj_seg,
            affine_file=affine_file,
            subject=subject,
            session=session
        )

        warped_best_seg = ants.image_read(os.path.join(scratch_dir, "warped_regionals.nii.gz"))


        unique_label_t2 = np.unique(fixed_seg.numpy())
        if 4 in unique_label_t2:
            seg_array = fixed_seg.numpy()
            seg_array[seg_array == 4] = 2

            fixed_seg = ants.from_numpy(seg_array, origin=fixed_seg.origin, spacing=fixed_seg.spacing,
                                            direction=fixed_seg.direction)

        new_data = np.zeros_like(warped_best_seg.numpy(), dtype=np.uint8)

        new_data[(warped_best_seg.numpy() == 1) & (fixed_seg.numpy() == 1)] = 1  # Right CSF
        new_data[(warped_best_seg.numpy() == 1) & (fixed_seg.numpy() == 2)] = 2  # Right WM
        new_data[(warped_best_seg.numpy() == 1) & (fixed_seg.numpy() == 3)] = 3  # Right GM
        new_data[(warped_best_seg.numpy() == 1) & (fixed_seg.numpy() == 4)] = 2  # merge right ventricule into wm

        new_data[(warped_best_seg.numpy() == 2) & (fixed_seg.numpy() == 1)] = 5  # Left CSF
        new_data[(warped_best_seg.numpy() == 2) & (fixed_seg.numpy() == 2)] = 6  # Left WM
        new_data[(warped_best_seg.numpy() == 2) & (fixed_seg.numpy() == 3)] = 7  # Left GM
        new_data[(warped_best_seg.numpy() == 2) & (fixed_seg.numpy() == 4)] = 6  # merge left ventricule into wm

        new_data[(warped_best_seg.numpy() == 3)] = 9  # Tronc
        new_data[(warped_best_seg.numpy() == 4)] = 10  # Cervelet

        seg_out = fixed_seg.new_image_like(new_data)
        ants.image_write(seg_out, file_seg_out)
        print("\tSplitted segmentation saved as:", file_seg_out)