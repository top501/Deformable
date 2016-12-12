

## ^^^ Leave two lines blank at top which will be filled by CMake BASIS

##############################################################################
# Medical Image Registration ToolKit (MIRTK)
#
# Copyright 2016 Imperial College London
# Copyright 2016 Andreas Schuh
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##############################################################################

"""Command-line tool for reconstruction of neonatal cortex

This command implements the deformable surfaces method for the reconstruction of
the neonatal cortex as detailed in the conference paper submission to ISBI 2017.

See -help output for details.
"""

import os
import re
import sys
import csv
import argparse
import traceback

try:
    from configparser import SafeConfigParser
except:
    from ConfigParser import SafeConfigParser

import mirtk.deformable.neonatal_cortex as neoctx


# ==============================================================================
# neonatal cortex reconstruction pipeline
# ==============================================================================

# ------------------------------------------------------------------------------
def get_default_config(work_dir='.', section='recon-neonatal-cortex'):
    """Get default configuration."""
    # directories
    session_dir = os.path.join('%(WorkDir)s', '%(SubjectID)s-%(SessionID)s')
    temp_dir    = os.path.join(session_dir, 'temp')
    image_dir   = os.path.join(session_dir, 'images')
    mask_dir    = os.path.join(session_dir, 'masks')
    mesh_dir    = os.path.join(session_dir, 'meshes')
    # configuration
    config  = SafeConfigParser(defaults={'work_dir': work_dir, 'temp_dir': temp_dir})
    section = args.section
    config.add_section(section)
    config.set(section, 't1w_image',            os.path.join(image_dir, 't1w.nii.gz'))
    config.set(section, 't2w_image',            os.path.join(image_dir, 't2w.nii.gz'))
    config.set(section, 'brain_mask',           os.path.join(mask_dir,  'brain.nii.gz'))
    config.set(section, 'white_matter_mask',    os.path.join(temp_dir,  'white-matter-mask.nii.gz'))
    config.set(section, 'gray_matter_mask',     os.path.join(temp_dir,  'gray-matter-mask.nii.gz'))
    config.set(section, 'corpus_callosum_mask', os.path.join(temp_dir,  'corpus-callosum-mask.nii.gz'))
    config.set(section, 'subcortex_mask',       os.path.join(temp_dir,  'subcortex-mask.nii.gz'))
    config.set(section, 'regions_mask',         os.path.join(mask_dir,  'regions.nii.gz'))
    config.set(section, 'cortical_hull_dmap',   os.path.join(temp_dir,  'cortical-hull-dmap.nii.gz'))
    config.set(section, 'ventricles_dmap',      os.path.join(temp_dir,  'ventricles-dmap.nii.gz'))
    config.set(section, 'brain_mesh',           os.path.join(mesh_dir,  'brain.vtp'))
    config.set(section, 'bs_cb_mesh',           os.path.join(mesh_dir,  'bs+cb.vtp'))
    config.set(section, 'internal_mesh',        os.path.join(mesh_dir,  'internal.vtp'))
    config.set(section, 'cerebrum_mesh',        os.path.join(temp_dir,  'cerebrum.vtp'))
    config.set(section, 'right_cerebrum_mesh',  os.path.join(temp_dir,  'cerebrum-rh.vtp'))
    config.set(section, 'left_cerebrum_mesh',   os.path.join(temp_dir,  'cerebrum-lh.vtp'))
    config.set(section, 'white_mesh',           os.path.join(mesh_dir,  'white.vtp'))
    config.set(section, 'right_white_mesh',     os.path.join(mesh_dir,  'white-rh.vtp'))
    config.set(section, 'left_white_mesh',      os.path.join(mesh_dir,  'white-lh.vtp'))
    config.set(section, 'pial_mesh',            os.path.join(mesh_dir,  'pial.vtp'))
    config.set(section, 'right_pial_mesh',      os.path.join(mesh_dir,  'pial-rh.vtp'))
    config.set(section, 'left_pial_mesh',       os.path.join(mesh_dir,  'pial-lh.vtp'))
    return config

# ------------------------------------------------------------------------------
def recon_neonatal_cortex(config, section, config_vars,
                          with_brain_mesh=False, with_bs_cb_mesh=True,
                          with_white_mesh=True, with_pial_mesh=True,
                          pial_outside_white_surface=False,
                          join_bs_cb_mesh=False, cut=True,
                          force=False, check=True, verbose=0):
    """Reconstruct surfaces of neonatal cortex."""

    # input/output file paths
    temp_dir             = config.get(section, 'temp_dir',             vars=config_vars)
    t1w_image            = config.get(section, 't1w_image',            vars=config_vars)
    t2w_image            = config.get(section, 't2w_image',            vars=config_vars)
    brain_mask           = config.get(section, 'brain_mask',           vars=config_vars)
    wm_mask              = config.get(section, 'white_matter_mask',    vars=config_vars) 
    gm_mask              = config.get(section, 'gray_matter_mask',     vars=config_vars) 
    regions_mask         = config.get(section, 'regions_mask',         vars=config_vars) 
    corpus_callosum_mask = config.get(section, 'corpus_callosum_mask', vars=config_vars) 
    subcortex_mask       = config.get(section, 'subcortex_mask',       vars=config_vars) 
    cortical_hull_dmap   = config.get(section, 'cortical_hull_dmap',   vars=config_vars) 
    ventricles_dmap      = config.get(section, 'ventricles_dmap',      vars=config_vars) 
    brain_mesh           = config.get(section, 'brain_mesh',           vars=config_vars) 
    bs_cb_mesh           = config.get(section, 'bs_cb_mesh',           vars=config_vars) 
    internal_mesh        = config.get(section, 'internal_mesh',        vars=config_vars) 
    cerebrum_mesh        = config.get(section, 'cerebrum_mesh',        vars=config_vars) 
    right_cerebrum_mesh  = config.get(section, 'right_cerebrum_mesh',  vars=config_vars) 
    left_cerebrum_mesh   = config.get(section, 'left_cerebrum_mesh',   vars=config_vars) 
    white_mesh           = config.get(section, 'white_mesh',           vars=config_vars) 
    right_white_mesh     = config.get(section, 'right_white_mesh',     vars=config_vars) 
    left_white_mesh      = config.get(section, 'left_white_mesh',      vars=config_vars) 
    pial_mesh            = config.get(section, 'pial_mesh',            vars=config_vars) 
    right_pial_mesh      = config.get(section, 'right_pial_mesh',      vars=config_vars) 
    left_pial_mesh       = config.get(section, 'left_pial_mesh',       vars=config_vars) 

    if not with_brain_mesh:
        brain_mesh = None
    if not with_bs_cb_mesh:
        bs_cb_mesh = None
    if not with_pial_mesh:
        pial_mesh = None
    if not os.path.isfile(t1w_image):
        t1w_image = None
    if not os.path.isfile(corpus_callosum_mask):
        corpus_callosum_mask = None

    if bs_cb_mesh and join_bs_cb_mesh:
        bs_cb_mesh_1 = bs_cb_mesh
        bs_cb_mesh_2 = None
    else:
        bs_cb_mesh_1 = None
        bs_cb_mesh_2 = bs_cb_mesh

    # reconstruct boundary of brain mask
    if brain_mesh and (force or not os.path.isfile(brain_mesh)):
        if verbose > 0:
            print("Reconstructing boundary of brain mask")
        neoctx.recon_brain_surface(name=brain_mesh, mask=brain_mask, temp=temp_dir)

    # reconstruct brainstem plus cerebellum surface
    if bs_cb_mesh and (force or not os.path.isfile(bs_cb_mesh)):
        if verbose > 0:
            print("Reconstructing brainstem plus cerebellum surface")
        neoctx.recon_brainstem_plus_cerebellum_surface(name=bs_cb_mesh, regions=regions_mask, temp=temp_dir)

    # reconstruct inner and/or outer cortical surfaces
    if with_white_mesh or with_pial_mesh:

        # reconstruct cortical surface from segmentation
        if force or not os.path.isfile(white_mesh):
            if force or not os.path.isfile(cerebrum_mesh):

                # reconstruct cortical surfaces of right and left hemispheres
                if force or not os.path.isfile(right_cerebrum_mesh):
                    if verbose > 0:
                        print("Reconstructing boundary of right cerebral hemisphere segmentation")
                    neoctx.recon_cortical_surface(name=right_cerebrum_mesh,
                                                  regions=regions_mask, hemisphere=neoctx.Hemisphere.Right,
                                                  corpus_callosum_mask=corpus_callosum_mask, temp=temp_dir)
                if force or not os.path.isfile(left_cerebrum_mesh):
                    if verbose > 0:
                        print("Reconstructing boundary of left cerebral hemisphere segmentation")
                    neoctx.recon_cortical_surface(name=left_cerebrum_mesh,
                                                  regions=regions_mask, hemisphere=neoctx.Hemisphere.Left,
                                                  corpus_callosum_mask=corpus_callosum_mask, temp=temp_dir)

                # join cortical surfaces of right and left hemispheres
                if verbose > 0:
                    print("Joining surfaces of right and left cerebral hemispheres")
                neoctx.join_cortical_surfaces(name=cerebrum_mesh, regions=regions_mask,
                                              right_mesh=right_cerebrum_mesh,
                                              left_mesh=left_cerebrum_mesh,
                                              bs_cb_mesh=bs_cb_mesh_1,
                                              internal_mesh=internal_mesh,
                                              temp=temp_dir, check=check)

                # remove cortical surfaces of right and left hemispheres
                if neoctx.debug < 1:
                    os.remove(right_cerebrum_mesh)
                    os.remove(left_cerebrum_mesh)

        # reconstruct white surface
        if force or not os.path.isfile(white_mesh):
            if verbose > 0:
                print("Reconstructing inner-cortical surface")
            neoctx.recon_white_surface(name=white_mesh,
                                       t1w_image=t1w_image, t2w_image=t2w_image,
                                       wm_mask=wm_mask, gm_mask=gm_mask,
                                       cortex_mesh=cerebrum_mesh, bs_cb_mesh=bs_cb_mesh_2,
                                       subcortex_mask=subcortex_mask,
                                       cortical_hull_dmap=cortical_hull_dmap,
                                       ventricles_dmap=ventricles_dmap,
                                       temp=temp_dir, check=check)
            # remove joined cortical surface mesh
            if neoctx.debug < 1:
                os.remove(cerebrum_mesh)

        # cut white surface at medial plane
        if cut and white_mesh and (force or not os.path.isfile(right_white_mesh)
                                         or not os.path.isfile(left_white_mesh)):
            if verbose > 0:
                print("Cutting inner-cortical surface at medial cutting plane")
            neoctx.split_cortical_surfaces(joined_mesh=white_mesh,
                                           right_name=right_white_mesh,
                                           left_name=left_white_mesh,
                                           internal_mesh=internal_mesh,
                                               temp=temp_dir)

        # reconstruct pial surface
        if pial_mesh and (force or not os.path.isfile(pial_mesh)):
            if verbose > 0:
                print("Reconstructing outer-cortical surface")
            neoctx.recon_pial_surface(name=pial_mesh, t2w_image=t2w_image,
                                      wm_mask=wm_mask, gm_mask=gm_mask, brain_mask=brain_mask,
                                      white_mesh=white_mesh, bs_cb_mesh=bs_cb_mesh_2,
                                      outside_white_mesh=pial_outside_white_surface,
                                      temp=temp_dir, check=check)

        # cut pial surface at medial plane
        if cut and pial_mesh and (force or not os.path.isfile(right_pial_mesh)
                                        or not os.path.isfile(left_pial_mesh)):
            if verbose > 0:
                print("Cutting outer-cortical surface at medial cutting plane")
            neoctx.split_cortical_surfaces(joined_mesh=pial_mesh,
                                           right_name=right_pial_mesh,
                                           left_name=left_pial_mesh,
                                           internal_mesh=internal_mesh,
                                           temp=temp_dir)

# ==============================================================================
# SLURM
# ==============================================================================

# ------------------------------------------------------------------------------
def sbatch(job_name, log_dir, session, args):
    """Submits SLURM jobs to run this script, one for each subject."""
    from subprocess import Popen, PIPE
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    outlog = os.path.join(log_dir, job_name + '-%j.out')
    errlog = os.path.join(log_dir, job_name + '-%j.err')
    p = Popen(['sbatch', '--mem=4G', '-n', '1', '-c', str(args.threads), '-p', args.queue, '-o', outlog, '-e', errlog, '-J', job_name], stdout=PIPE, stderr=PIPE, stdin=PIPE)
    args_map = {
        'script':  __file__,
        'config': args.config,
        'section': args.section,
        'work_dir':  args.work_dir,
        'session': session,
        'threads': args.threads,
        'verbose': ' '.join(['-v'] * args.verbose),
        'debug':   ' '.join(['-d'] * args.debug)
      }
    script  = "#!/bin/sh\nexec python3 {script} --threads={threads} {verbose} {debug}"
    script += " --work-dir={work_dir} --config={config} --section={section} --session={session}"
    if args.brain:   script += ' --brain'
    if args.white:   script += ' --white'
    if args.pial:    script += ' --pial'
    if args.force:   script += ' --force'
    if not args.cut: script += ' --nocut'
    if not args.check: script += ' --nocheck'
    if args.pial_outside_white:
        script += ' --ensure-pial-is-outside-white-surface'
    (out, err) = p.communicate(input=script.format(**args_map).encode('utf-8'))
    if p.returncode != 0:
        raise Exception(err)
    m = re.match('Submitted batch job ([0-9]+)', out)
    if m: return int(m.group(1))
    return out

# ==============================================================================
# main
# ==============================================================================

# parse arguments
parser = argparse.ArgumentParser(description='Reconstruct neonatal cortex from MR brain scan and Draw-EM segmentation')
parser.add_argument('-r', '-root', '--root', '-work-dir', '--work-dir', dest='work_dir', default=os.getcwd(), help='Root working directory')
parser.add_argument('-c', '-config', '--config', default='', help='Optional custom configuration file')
parser.add_argument('-section', '--section', default='recon-neonatal-cortex', help='Configuration section name')
parser.add_argument('-s', '-sessions', '--sessions', default=[], nargs='+', help="Either list of '{SubjectID}-{SessionID}' strings or path of CSV file")
parser.add_argument('-b', '-brain', '--brain', action='store_true', help='Reconstruct surface of brain mask')
parser.add_argument('-w', '-white', '--white', action='store_true', help='Reconstruct white surface')
parser.add_argument('-p', '-pial', '--pial', action='store_true', help='Reconstruct pial surface')
parser.add_argument('-ensure-pial-is-outside-white-surface', '--ensure-pial-is-outside-white-surface',
                    dest='pial_outside_white', action='store_true', help='Ensure that pial surface is strictly outside the white surface')
parser.add_argument('-nocut', '-nosplit', '--nocut', '--nosplit', dest='cut', action='store_false', help='Save individual (closed) genus-0 surfaces for each hemisphere')
parser.add_argument('-nocheck', '--nocheck', action='store_false', dest='check', help='Disable consistency and self-intersection checks of (intermediate) surface meshes')
parser.add_argument('-f', '-force', '--force', action='store_true', help='Overwrite existing output files')
parser.add_argument('-v', '-verbose', '--verbose', action='count', default=0, help='Increase verbosity of output messages')
parser.add_argument('-d', '-debug', '--debug', action='count', default=0, help='Keep/write debug output in temp_dir')
parser.add_argument('-t', '-threads', '--threads', default=0, help='No. of cores to use for multi-threading')
parser.add_argument('-q', '-queue', '--queue', default='', help='SLURM partition/queue')

args = parser.parse_args()
args.work_dir = os.path.abspath(args.work_dir)
if not args.white and not args.pial:
    args.white = True
    args.pial  = True
elif args.pial:
    args.white = True

# read configuration
config = get_default_config(work_dir=args.work_dir, section=args.section)
config.read(os.path.join(args.work_dir, 'recon-neonatal-cortex.cfg'))
if args.config:
    with open(args.config, 'r') as config_file:
        config.readfp(config_file)

# set global flags
neoctx.verbose = max(0, args.verbose - 1)
neoctx.showcmd = max(0, args.verbose - 1)
neoctx.debug   = max(0, args.debug)
neoctx.force   = args.force

# use default CSV file if no sessions specified
if len(args.sessions) == 0:
    csv_name = os.path.join(args.work_dir, 'subjects.csv')
    if not os.path.isfile(csv_name):
        sys.stderr.write("Neither --sessions specified nor default CSV file found: {}".format(csv_name))
        sys.exit(1)
    args.sessions = [csv_name]

# read subject and session IDs from CSV file
if len(args.sessions) == 1 and os.path.isfile(args.sessions[0]):
    csv_name = args.sessions[0]
    sessions = []
    with open(csv_name) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'SessionID' in row:
                sessions.append('{SubjectID}-{SessionID}'.format(**row))
            else:
                sessions.append('{SubjectID}'.format(**row))
else:
    sessions = args.sessions

# for each session...
failed = 0
for session in sessions:
    match = re.match('^(.*)-([^-]+)$', session)
    if match:
        subject_id = match.group(1)
        session_id = match.group(2)
    else:
        subject_id = session
        session_id = '0'
        session = session + '-0'
    info = {
      'subid':      subject_id,
      'subject_id': subject_id,
      'subjectid':  subject_id,
      'SubjectID':  subject_id,
      'SubjectId':  subject_id,
      'sesid':      session_id,
      'session_id': session_id,
      'sessionid':  session_id,
      'SessionID':  session_id,
      'SessionId':  session_id,
      'WorkDir':    args.work_dir,
      'work_dir':   args.work_dir
    }
    try:
        if args.queue:
            sys.stdout.write("Submitting SLURM job for {SubjectID} session {SessionID}: ".format(**info))
            job_name = 'rec-{SubjectID}-{SessionID}'.format(**info)
            log_dir  = os.path.join(args.work_dir, session, 'logs')
            job_id   = sbatch(job_name, log_dir, session, args)
            sys.stdout.write('Job ID = {}\n'.format(job_id))
        else:
            sys.stdout.write("\nReconstructing cortical surfaces of {SubjectID} session {SessionID}\n".format(**info))
            recon_neonatal_cortex(config=config, section=args.section, config_vars=info,
                                  with_brain_mesh=args.brain,
                                  with_white_mesh=args.white,
                                  with_pial_mesh=args.pial,
                                  pial_outside_white_surface=args.pial_outside_white,
                                  verbose=args.verbose,
                                  check=args.check)
    except Exception as e:
        failed += 1
        if args.queue:
            sys.stdout.write("failed\n")
        sys.stdout.write("\n")
        if args.verbose > 0 or args.debug > 0:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
        else:
            sys.stderr.write('Exception: {}\n'.format(str(e)))
if failed > 0:
    sys.exit(1)