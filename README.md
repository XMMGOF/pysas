### Installing pySAS

This version of pySAS can be used with versions 20 and up of XMM-Newton SAS. After installing SAS [following the installation instructions](https://www.cosmos.esa.int/web/xmm-newton/sas-installation) you can then install the development version of pySAS using
```
pip install xmmpysas
```
**Note:** Make sure you install **xmmpysas**. There is different Python module called *pysas* that has nothing to with pySAS for XMM-Newton.

**Note:** Requires Python version >=3.10.

Before you use pySAS for the first time you will need to configure pySAS so that it knows where you have SAS installed, and where the XMM calibration files are located. After installing pySAS using pip, in Python just run:
```python
import pysas
pysas.config_pysas.run_config()
```
This will step you through connecting pySAS to SAS. After pySAS has been configured you can import pySAS like normal.
```python
import pysas
```
You can update pySAS using
```
pip install xmmpysas --upgrade
```
### Example Scripts

There are example scripts and Jupyter notebooks available on [GitHub demonstrating how to use pySAS](https://github.com/XMMGOF/pysas_docs). We are expanding the number of example scripts and Jupyter notebooks. You can clone the repository with the example notebooks by running the following command in a directory of your choosing:

```
git clone https://github.com/XMMGOF/pysas_docs.git
```

With the documentation on GitHub there are notebooks explaining the [basics of pySAS](https://github.com/XMMGOF/pysas_docs/blob/master/Basics_of_pySAS.ipynb), and using [pySAS v2.0](https://github.com/XMMGOF/pysas_docs/blob/master/Using_pySASv2.ipynb).

### Running pySAS for the First Time

The very first time you run this version of pySAS you will have to set SAS defaults that will be used by pySAS. To set the defaults run the following commands in python:
```python
import pysas
pysas.config_pysas.run_config()
```
This script will set:

- sas_dir: The directory where SAS is installed. If you are running the script from inside the SAS directory this will be auto-detected.
- sas_ccfpath: The directory where the calibration files are stored. If you already have them downloaded, just enter the directory where they are. But if you have not downloaded them yet, you will be given the option to download them after the setup. The script will even create the directory for you.
- data_dir: You will have the option of designating a defaut data directory. All observation data files will be downloaded into this directory. If the data directory does not exist it will be created for you.

**Note:** If you installed pySAS by cloning it from GitHub you must add the pySAS directory to your PYTHONPATH environment variable. For example:
```
export PYTHONPATH=/path/to/sas/install/xmmsas_202XXXXXX_YYYY/lib/python:$PYTHONPATH
```
It is recommended that you add this line to your .bash_profile file (or equivelent shell file).
**This is not necessary if pySAS was installed using `pip install xmmpysas`.**

### Cloning This Repository

*Alternatively*, pySAS can be cloned from GitHub by going into the directory where pySAS is installed to remove the current version of pySAS using 
```
cd /path/to/sas/install/xmmsas_202XXXXXX_YYYY/lib/python/
rm -rf ./pysas
```
and then clone this version of pySAS by executing the command,
```
git clone https://github.com/XMMGOF/pysas.git
```
You can then use pySAS like normal.

To incorporate new changes to pySAS from GitHub, from the pysas directory use the following command,
```
git pull https://github.com/XMMGOF/pysas.git
```

### FAQ

Q: Will this break my SAS inatallation?

A: No. All changes have been made to keep this version of pySAS working with SAS.

Q: I have already been working with pySAS and I have several Python scripts already written. Will this make them break?

A: No. This version of pySAS is fully backwards compatible with the standard pySAS distributed with SAS. This version only adds capabilites. The features included here will eventually work their way into the standard version of pySAS.

Q: Can I contribute changes to pySAS?

A: YES! That is the purpose of this repository! The whole idea is to provide a place where changes can be made and tested, issues can be raised, and features can be requested for pySAS. User input is greatly encouraged.

Q: Can I use pip to install pySAS?

A: Yes! Install using
```
pip install xmmpysas
```

Q: What about using conda to install pySAS?

A: We are working on it!

Q: Can I use pySAS to update the XMM-Newton calibration files?

A: Yes! Just start a Python session and run the following commands:

```python
import pysas
pysas.sasutils.update_calibration_files()
```

This will download new calibration files.

Q: What version of pySAS is installed on SciServer?

A: Version 2.0.

Q: Why have this version of pySAS separate from the standard version you can download from ESA when you download SAS?

A: Because of the realities of developing across multiple systems. Changes were needed to make pySAS run on systems such as SciServer (and other future online systems that are in the works, stay tuned!). The development timetable for SciServer did not match up with the development timetable for SAS. This allows us to continuously develop pySAS to match *all* of the development timetables. This also allows us to get feedback from the XMM-Newton user community about what they want to see in pySAS.
