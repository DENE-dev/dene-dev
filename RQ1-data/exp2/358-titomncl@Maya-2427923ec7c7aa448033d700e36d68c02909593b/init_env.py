def main():
    import os
    import sys

    print("let's go")

    ############ HOT-FIX ############
    os.environ["PFE_PROJET"] = "G:/.shortcut-targets-by-id/1LKqbnGUt5-Lrfl9lElekEI0vY2DOIoog/VSPA"

    ############ USER PROFILE ############
    USER_PATH = os.environ['USERPROFILE'].replace('\\', '/')
    print(USER_PATH.upper())

    ############ ADD IPM IN PYTHONPATH ############
    sys.path.append(USER_PATH + "/ISART_PROJECT_MANAGER/")
    sys.path.append(USER_PATH + '/ISART_PROJECT_MANAGER/PY/')

    ### ISART PROJECT MANAGER PACKAGE ###
    import ipm
    import Vinci

    from globals import ROOT_PATH

    ### VARIABLES GENERALES ###
    NOM_PROJET = ipm.ctFindProject()

    if NOM_PROJET:
        print('NOM_PROJET : %s' % NOM_PROJET)
        LISTE_PERSOS = ipm.ctFindAsset(NOM_PROJET, 'CHARA\\*')
        print('LISTE_PERSOS : %s' % ' '.join(LISTE_PERSOS))
        LISTE_MODULES = ipm.ctFindAsset(NOM_PROJET, 'SET\\*\\MODULES\\*')
        print('LISTE_MODULES : %s' % ' '.join(LISTE_MODULES))

    ############# PFE ENV #############
    import os
    import sys

    PFE_ENV = ROOT_PATH + "/" + NOM_PROJET
    print(PFE_ENV)
    DEV_ENV = "E:/DEV"

    if os.path.isdir(DEV_ENV):
        venv = DEV_ENV + "/venv/Lib/site-packages"
    else:
        DEV_ENV = PFE_ENV + "/DEV/main"
        venv = DEV_ENV + "/venv/Lib/site-packages"

    sys.path.append(PFE_ENV)
    sys.path.append(DEV_ENV)
    sys.path.append(venv)

    os.environ["PFE_ENV"] = PFE_ENV
    os.environ["DEV_ENV"] = DEV_ENV

    ############ HOT-FIX ############
    os.environ["PFE_PROJET"] = PFE_ENV

    ########### PFE ENV END ###########

    ### MENU ISART ###
    import maya.cmds as cmds
    import maya.mel as mel
    cmds.evalDeferred('ipm.ctIsartMenu_UI()')

    ########## AUTO UDPATE ##########
    from Maya import common_

    cmds.evalDeferred('common_.update_user_setup()')