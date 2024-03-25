# ESA (C) 2000-2020
# 
# This file is part of ESA's XMM-Newton Scientific Analysis System (SAS).
#
#    SAS is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    SAS is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with SAS.  If not, see <http://www.gnu.org/licenses/>.
#
# pkgmaker.py
#
# (C) 2020 ESA
#
# Script to create the basic structure of any SAS task regardless of 
# being a task based on C++, Fortran, Perl or Python.
#
# The first version of this script was coded in Perl and created mainly
# the directory structure for a new task.
#
# This one, entirely rewriten in Python, does the same but, for Python, 
# it creates also all the software files required to build a real 
# Python package according to the Python Packaging standard 
# (see the Python Packaging User Guide).
#
# This script is aimed to create new SAS packages which include one or
# more tasks. 

# Standard library imports
import sys, os, shutil
from datetime import date

# Third Party imports


# Local app imports
from .version import VERSION, SAS_RELEASE, SAS_AKA


__version__ = f'pkgmaker (pkgmaker-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]'


def run(iparsdic):

    # current date and year in string format
    today = date.today()
    creationyear = today.year
    creationdate = today.strftime('%d-%b-%Y')
    creationdate_chlog = today.strftime('%Y-%m-%d')


    # SAS_DIR and SAS_PATH must be defined

    try:
        os.environ['SAS_DIR']
    except KeyError:
        print ("Your environment does not define SAS_DIR\n")
        sys.exit(1)

    sasdir = os.environ['SAS_DIR']

    try:
        os.environ['SAS_PATH']
    except KeyError:
        print ("Your environment does not define SAS_PATH\n")
        sys.exit(1)

    saspath = os.environ['SAS_PATH'].split(':')

    # Additional check: SAS_DIR must be equal to saspath[1] 

    if ( saspath[1] != sasdir ):
        print(f'Error: pkgmaker: Mismatching paths\n{saspath[1]}\n{sasdir}')
        sys.exit(1)

    # The base of the user´s development tree is saspath[0]
    # Let us call it sasdevbase

    sasdevbase = saspath[0]


    # Directories
    
    # Until now, basic code skeletons for tasks written in C++, Fortran90,
    # and Perl were put in the src directory as module.cc, module.f90 and
    # module.pl. A first attempt to create a basic skeleton for a Python task
    # named module.py, was also placed there. In all cases, these files
    # were simple hints on how to create the basic structure for the main
    # program of the task in the specific language.
    #
    # With Python we are changing that philosophy to provide both, the
    # directory structure and the files required to build and install
    # a real Python package.
    #
    # With pkgmaker we can create 4 types of SAS packages: C++ (cpp),
    # Fortran90 (fortran), Perl (perl) and Python (python).
    # Those packages may include either one or several tasks.
    #
    # Package templates will be all below pkgtemplate
    #
    #    pkgtemplate = os.path.join(sasdir, 'packages/pkgmaker/template')
    #
    # Each type of package, has its own templatedir
    #
    #     templatedir = os.path.join(pkgtemplate, 'python')
    #                   os.path.join(pkgtemplate, 'cpp')
    #                   os.path.join(pkgtemplate, 'fortran')
    #                   os.path.join(pkgtemplate, 'perl')


    # home is the user´s home directory

    home = os.environ['HOME']

    # Below sasdevbase, developers use to have the SAS git clone,
    # typically named 'sas', which, together with sasdevbase forms
    # sasdev. 

    sasdev = os.path.join(home, sasdevbase + '/sas')

    if not os.path.exists(sasdev):
        print(f"""

        Directory {sasdev} does not exist. 

        Possibly your SAS git clone is not named sas. 

        Please create soft link and rerun pkgmaker.
        
        """)
        sys.exit(1)


    # The following chain of directories is based on sasdir
    #
    # pkgmakerdir is the directory of package pkgmaker
    # pkgtemplate is the directory with the pkgmaker templates

    pkgmakerdir = os.path.join(sasdir, 'packages/pkgmaker')
    pkgtemplate = os.path.join(sasdir, 'packages/pkgmaker/template')

    # packagesdir is where new packages will be written

    packagesdir = os.path.join(sasdev, 'packages')


    # Initial values for taskStatus and taskVersion

    pkgstatus = 'Draft'  # Draft/Submitted/Approved
    pkgversion = '0.1'

    # Begin asking information about the new package

    print(f"""
    
    SAS package maker 
    
    Version: {__version__}

    *

    New SAS packages will be placed in: {packagesdir}
    
    """)

    pkgname = input("\n\nEnter the name of the new package: ")

    # Change dir to packagesdir to check whether pkgname exists or not

    os.chdir(packagesdir)

    if not(os.path.exists(pkgname)):
        os.mkdir(pkgname)
        print(f"\nCreated directory for package {pkgname}")
    else:
        print(f"Error: Directory {pkgname} already exists!")
        sys.exit(1)

    # Request type of package

    pkgtype = {
            '1': 'cpp',
            '2': 'fortran',
            '3': 'perl',
            '4': 'python'
            }

    print("""
    
    Select package programming language:
            
            1 - c++       (cpp)
            2 - fortran   (fortran)
            3 - perl      (perl)
            4 - python    (python)
    
    Default 4 - python
    
    """)

    sel = input("Select 1, 2, 3, 4 : ")

    if sel == "":
        sel = '4'

    if sel in '1234':
        templatedir = os.path.join(pkgtemplate, pkgtype[sel])
        print(f"\nPackage {pkgname} is of type {pkgtype[sel]}")
    else:
        print(f"\nError: Unknown option {sel} ")
        sys.exit(1)

    print(f"""
    
    Package {pkgname} can have one or more tasks.
    
    Will give name to one!
    
    """)

    taskname = input(f'\n\n\nEnter a task name (Default: {pkgname} - <Hit ENTER>): ')
    if not taskname:
        taskname = pkgname

    # Extension of the main program
    taskext = {
        '1': '.cc',
            '2': '.f90',
            '3': '.pl',
            '4': '.py'
            }
    # Sign for comments depends on language
    commentsign = {
            '1': '//',
            '2': '!',
            '3': '#',
            '4': '#'
            }


    # Define home for pkgname

    pkgnamedir = os.path.join(packagesdir, pkgname)

    # Change dir to pkgname

    os.chdir(pkgname)


    # Create the package directory structure similar for all packages

    for dirname in ('src', 'config', 'doc', 'test'):
        os.mkdir(dirname)

    # Fills in the VERSION file with the initial version of the package
    with open('VERSION', 'w') as outf:
        string = pkgversion + '\n' # It requires to append an \n
        outf.write(string)

    # Copy DEPEND and DISTRIBUTION from the tasktemplate directory
    # These are common to all packages
    # Perhaps in a future version of this script, we can request to enter
    # the value of DISTRIBUTION
    shutil.copy(os.path.join(pkgtemplate, 'DEPEND'), '.')
    shutil.copy(os.path.join(pkgtemplate, 'DISTRIBUTION'), '.')

    # Package description

    pkgdescription = input("\nEnter a one-line description of the package: ")

    print(f"""
    
    Package {pkgname} type {pkgtype[sel]} will receive version {pkgversion} and status {pkgstatus}. 
    
    You may want to change these in the LaTeX description document 
    
                 doc/{pkgname}_description.tex 
    
    or in the main program source code
    
                 src/{pkgname}/{pkgname}{taskext[sel]}
    
    
    Now, please enter the names of author(s) of the package, their affiliation(s)
    and email address(es).
    
    """
    )

    authors = input(f"\n\nEnter author(s) for {pkgname} separated by commas: ")
    pkgauthors = authors.split(',')
    for k in range(len(pkgauthors)):
        pkgauthors[k] = pkgauthors[k].strip()

    affiliations = ['a']*len(pkgauthors)
    for k in range(len(pkgauthors)):
        affiliations[k] = input(f"\n\nAffiliation for {pkgauthors[k]}: ")

    emails = ['a']*len(pkgauthors)
    for k in range(len(pkgauthors)):
        emails[k] = input(f"\n\ne-mails for {pkgauthors[k]}: ")

    class Authorscard:
        def __init__(self, author, affiliation, email):
            self.author = author
            self.affiliation = affiliation
            self.email = email

        def __str__(self):
            return(f"{self.author} - {self.affiliation} - {self.email}")

    print("\nPackage authors card:\n")

    authorsvcard = '\n' + commentsign[sel] + '\t\t'
    authorsvcard_tex = '\n\t\t'
    vcard = ['a']*len(pkgauthors)
    for k in range(len(pkgauthors)):
        vcard[k] = Authorscard(pkgauthors[k], affiliations[k], emails[k])
        authorsvcard += str(vcard[k]) + '\n' + commentsign[sel] + '\t\t'
        authorsvcard_tex += str(vcard[k]) + '\n\t\t'
    print(authorsvcard)
    print(authorsvcard_tex)

    pkgauthors_str = ''
    emails_str = ''
    for k in range(len(pkgauthors)):
        if (k != (len(pkgauthors) - 1) ):
            pkgauthors_str += pkgauthors[k] + ' - '
            emails_str += emails[k] + ' - '
            continue
        pkgauthors_str += pkgauthors[k]
        emails_str += emails[k]



    # Write the files which are required by all type of packages
    #
    # pkgtemplate/Changelog.in
    #                                  => pkgnamedir/ChangeLog
    # pkgtemplate/Makefile.in
    #                                  => pkgnamedir/Makefile
    #
    # pkgtemplate/doc/package_description.tex.in
    #                                  => pkgnamedir/doc/pkgname_description.tex
    # pkgtemplate/doc/Makefile.in
    #                                  => pkgnamedir/doc/Makefile
    #
    # pkgtemplate/config/Makefile.in
    #                                  => pkgnamedir/config/Makefile
    # pkgtemplate/config/task.par.in
    #                                  => pkgnamedir/config/pkgname.par
    # pkgtemplate/config/pkg.info.in
    #                                  => pkgnamedir/config/pkgname.info
    #
    # pkgtemplate/test/Makefile.in
    #                                  => pkgnamedir/test/Makefile
    # pkgtemplate/test/notest.in
    #                                  => pkgnamedir/test/notest
    #
    #

    # In C/C++ and Perl programs and in TeX/LaTeX documents the symbols
    # { and } are used to delimit main programs, subroutines and typesetting
    # commands, therefore the "in" files can not have them as such because
    # they will conflict with the delimiters of the variable names {variable}.
    # To solve this problem, we define cb and ce as strings containing only
    # those symbols so we can write them to the output file.
    cb = '{'
    ce = '}'


    with open(os.path.join(pkgtemplate, 'ChangeLog.in')) as inf, \
            open((os.path.join(pkgnamedir, 'ChangeLog')), 'w') as outf:
         template = inf.read()
         outf.write(template.format(pkgname=pkgname,
                                    pkgversion=pkgversion,
                                    creationdate_chlog=creationdate_chlog))

    # For Python based packages, the input file is Makefile.python.in
    if sel in ['1', '2', '3']:
        with open(os.path.join(pkgtemplate, 'Makefile.in')) as inf, \
                open((os.path.join(pkgnamedir, 'Makefile')), 'w') as outf:
         template = inf.read()
         outf.write(template.format(creationyear=creationyear))

    fileout = 'doc/' + pkgname + '_description.tex'
    cb = '{'
    ce = '}'
    with open(os.path.join(pkgtemplate, 'doc/package_description.tex.in')) as inf, \
            open((os.path.join(pkgnamedir, fileout)), 'w') as outf:
         template = inf.read()
         outf.write(template.format(cb=cb,
                                    ce=ce,
                                    creationyear=creationyear,
                                    pkgname=pkgname,
                                    creationdate=creationdate,
                                    pkgdescription=pkgdescription,
                                    authorsvcard=authorsvcard_tex,
                                    pkgversion=pkgversion,
                                    pkgstatus=pkgstatus))

    fileout = 'doc/Makefile'
    with open(os.path.join(pkgtemplate, 'doc/Makefile.in')) as inf, \
            open((os.path.join(pkgnamedir, fileout)), 'w') as outf:
         template = inf.read()
         outf.write(template.format(creationyear=creationyear,
                                    pkgname=pkgname))

    fileout = 'config/Makefile'
    with open(os.path.join(pkgtemplate, 'config/Makefile.in')) as inf, \
            open((os.path.join(pkgnamedir, fileout)), 'w') as outf:
         template = inf.read()
         outf.write(template.format(creationyear=creationyear,
                                    taskname=taskname,
                                    pkgname=pkgname))

    fileout = 'config/' + taskname + '.par'
    with open(os.path.join(pkgtemplate, 'config/task.par.in')) as inf, \
            open((os.path.join(pkgnamedir, fileout)), 'w') as outf:
         template = inf.read()
         outf.write(template.format(creationyear=creationyear,
                                    taskname=taskname))

    fileout = 'config/' + taskname + '.info'
    with open(os.path.join(pkgtemplate, 'config/task.info.in')) as inf, \
            open((os.path.join(pkgnamedir, fileout)), 'w') as outf:
         template = inf.read()
         outf.write(template.format(creationyear=creationyear,
                                    taskname=taskname,
                                    pkgdescription=pkgdescription))

    fileout = 'test/Makefile'
    with open(os.path.join(pkgtemplate, 'test/Makefile.in')) as inf, \
            open((os.path.join(pkgnamedir, fileout)), 'w') as outf:
         template = inf.read()
         outf.write(template.format(creationyear=creationyear))

    fileout = 'test/notest'
    with open(os.path.join(pkgtemplate, 'test/notest.in')) as inf, \
            open((os.path.join(pkgnamedir, fileout)), 'w') as outf:
         template = inf.read()
         outf.write(template.format(creationyear=creationyear,
                                    taskname=taskname))
         # Make notest mode 755
         os.chmod(os.path.join(pkgnamedir, fileout),0o755)

    # Write the source code templatefor a task for each type of package

    # 1 - Package type c++

    if (sel == '1'):
        # module.cc.in => module.cc
        taskmodulein = 'module' + taskext[sel] + '.in'
        taskmodule   = taskname + taskext[sel]
        #print(f"                                     \n \
        #        pkgnamedir       = {pkgnamedir}      \n \
        #        taskmodulein     = {taskmodulein}    \n \
        #        taskmodule       = {taskmodule}      \n \
        #        templatedir      = {templatedir}     \n \
        #        creationyear     = {creationyear}    \n \
        #        creationdate     = {creationdate}    \n \
        #        pkgdescription   = {pkgdescription}  \n \
        #        authorsvcard     = {authorsvcard}")
        #

        with open(os.path.join(templatedir, taskmodulein)) as inf, \
                open((os.path.join('src', taskmodule)), 'w') as outf:
            template = inf.read()
            outf.write(template.format(creationyear=creationyear,
                                       taskname=taskname,
                                       creationdate=creationdate,
                                       pkgdescription=pkgdescription,
                                       authorsvcard=authorsvcard,
                                       cb=cb,
                                       ce=ce))

        with open(os.path.join(templatedir, 'Makefile.in')) as inf, \
                open((os.path.join('src', 'Makefile')), 'w') as outf:
            template = inf.read()
            outf.write(template.format(creationyear=creationyear,
                                       taskname=taskname))

    # 2 - Package type fortran
    elif(sel == '2'):
        # module.f90.in => pkgname_mod.f90
        taskname_mod = taskname + '_mod'
        taskmodulein = 'module' + taskext[sel] + '.in'
        taskmodule   = taskname_mod + taskext[sel]
        #print(f"                                     \n \
        #        pkgnamedir       = {pkgnamedir}      \n \
        #        taskmodulein     = {taskmodulein}    \n \
        #        taskmodule       = {taskmodule}      \n \
        #        templatedir      = {templatedir}     \n \
        #        creationyear     = {creationyear}    \n \
        #        creationdate     = {creationdate}    \n \
        #        pkgdescription   = {pkgdescription}  \n \
        #        authorsvcard     = {authorsvcard}")
        #
        with open(os.path.join(templatedir, taskmodulein)) as inf, \
                open((os.path.join('src', taskmodule)), 'w') as outf:
            template = inf.read()
            outf.write(template.format(creationyear=creationyear,
                                       taskname=taskname,
                                       creationdate=creationdate,
                                       pkgdescription=pkgdescription,
                                       authorsvcard=authorsvcard,
                                       taskname_mod=taskname_mod))

        with open(os.path.join(templatedir, 'Makefile.in')) as inf, \
                open((os.path.join('src', 'Makefile')), 'w') as outf:
            template = inf.read()
            outf.write(template.format(creationyear=creationyear,
                                       taskname=taskname,
                                       taskname_mod=taskname_mod))


    # 3 - Package type perl
    elif(sel == '3'):
        # module.pl.in => pkgname.pl
        taskmodulein = 'module' + taskext[sel] + '.in'
        taskmodule   = taskname + taskext[sel]
        #print(f"                                     \n \
        #        pkgnamedir       = {pkgnamedir}      \n \
        #        taskmodulein     = {taskmodulein}    \n \
        #        taskmodule       = {taskmodule}      \n \
        #        templatedir      = {templatedir}     \n \
        #        creationyear     = {creationyear}    \n \
        #        creationdate     = {creationdate}    \n \
        #        pkgdescription   = {pkgdescription}  \n \
        #        authorsvcard     = {authorsvcard}")
        #
        with open(os.path.join(templatedir, taskmodulein)) as inf, \
                open((os.path.join('src', taskmodule)), 'w') as outf:
            template = inf.read()
            outf.write(template.format(creationyear=creationyear,
                                       taskname=taskname,
                                       creationdate=creationdate,
                                       pkgdescription=pkgdescription,
                                       authorsvcard=authorsvcard,
                                       cb=cb,
                                       ce=ce))

        with open(os.path.join(templatedir, 'Makefile.in')) as inf, \
                open((os.path.join('src', 'Makefile')), 'w') as outf:
            template = inf.read()
            outf.write(template.format(creationyear=creationyear,
                                       taskname=taskname))

    # 4 - Package type python
    elif (sel == '4'):

        classname = 'MyTask'

        os.mkdir(os.path.join('src', pkgname))
        os.mkdir(os.path.join('src', pkgname, 'bin'))

        # Replace Makefile in root dir by Makefile.python.in
        with open(os.path.join(pkgtemplate, 'Makefile.python.in')) as inf, \
                open((os.path.join(pkgnamedir, 'Makefile')), 'w') as outf:
            template = inf.read()
            outf.write(template.format(creationyear=creationyear,
                                       pkgname=pkgname))

        # Create README.md from README.md.in
        with open(os.path.join(templatedir, 'README.md.in')) as inf, \
                open((os.path.join(pkgnamedir, 'README.md')), 'w') as outf:
            template = inf.read()
            outf.write(template.format(pkgname=pkgname))

        # Create Makefile from Makefile.taskname.in
        with open(os.path.join(templatedir, 'Makefile.taskname.in')) as inf, \
                open((os.path.join('src', pkgname, 'Makefile')), 'w') as outf:
            template = inf.read()
            outf.write(template.format(creationyear=creationyear))

        # Create Makefile from Makefile.taskname.bin.in
        with open(os.path.join(templatedir, 'Makefile.taskname.bin.in')) as inf, \
                open((os.path.join('src', pkgname, 'bin', 'Makefile')), 'w') as outf:
            template = inf.read()
            outf.write(template.format(creationyear=creationyear,
                                       taskname=taskname))


        # Create setup.py from setup.py.in
        with open(os.path.join(templatedir, 'setup.py.in')) as inf, \
                open('setup.py', 'w') as outf:
                template = inf.read()
                outf.write(template.format(author=pkgauthors_str,
                                           author_email=emails_str,
                                           pkgname=pkgname,
                                           description=pkgdescription,
                                           taskversion=pkgversion,
                                           taskname=taskname))

        # Create src/pkgname/__init__.py
        with open(os.path.join(templatedir, '__init__.py.in')) as inf, \
                open(os.path.join('src', pkgname, '__init__.py'), 'w') as outf:
                template = inf.read()
                outf.write(template.format(taskname=taskname))

        # Create src/pkgname/taskname.py
        with open(os.path.join(templatedir, 'taskname.py.in')) as inf, \
                open(os.path.join('src', pkgname, f'{taskname}.py'), 'w') as outf:
                template = inf.read()
                outf.write(template.format(creationyear=creationyear,
                                           taskname=taskname,
                                           cb=cb,
                                           ce=ce))

        # Create src/pkgname/bin/taskname
        with open(os.path.join(templatedir, 'taskname.in')) as inf, \
                open(os.path.join('src', pkgname, 'bin', taskname), 'w') as outf:
                template = inf.read()
                outf.write(template.format(creationyear=creationyear,
                                           taskname=taskname,
                                           classname=classname))
                os.chmod(os.path.join('src', pkgname, 'bin', taskname), 0o755)

        # Copy template/python/version.py.in and template/python/write_version.py to 
        # src/pkgname
        shutil.copy(os.path.join(templatedir, 'version.py.in'), \
                os.path.join('src', pkgname))
        shutil.copy(os.path.join(templatedir, 'write_version.py'), \
                os.path.join('src', pkgname))
        # Copy specific DEPEND files for Python packages
        shutil.copy(os.path.join(templatedir, 'DEPEND'), '.')
    else:
        sys.exit(1)
