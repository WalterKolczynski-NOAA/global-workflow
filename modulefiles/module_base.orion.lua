help([[
Load environment to run GFS on Orion
]])

prepend_path("MODULEPATH", "/work/noaa/epic-ps/role-epic-ps/miniconda3/modulefiles")

load(pathJoin("miniconda3", "4.12.0"))

prepend_path("MODULEPATH", "/work/noaa/epic-ps/role-epic-ps/hpc-stack/libs/intel-2022.1.2/modulefiles/stack")

load(pathJoin("hpc", "1.2.0"))
load(pathJoin("hpc-intel", "2022.1.2"))
load(pathJoin("hpc-impi", "2022.1.2"))

load(pathJoin("gempak", "7.5.1"))
load(pathJoin("ncl", "6.6.2"))
load(pathJoin("jasper", "2.0.25"))
load(pathJoin("zlib", "1.2.11"))
load(pathJoin("libpng", "1.6.37"))
load(pathJoin("cdo", "1.9.5"))

load(pathJoin("hdf5", "1.10.6"))
load(pathJoin("netcdf", "4.7.4"))

load(pathJoin("nco", "4.8.1"))
load(pathJoin("prod_util", "1.2.2"))
load(pathJoin("grib_util", "1.2.4"))
load(pathJoin("g2tmpl", "1.10.0"))
load(pathJoin("ncdiag", "1.0.0"))
load(pathJoin("crtm", "2.4.0"))
load(pathJoin("wgrib2", "2.0.8"))

load(pathJoin("met", "10.1.2"))
load(pathJoin("metplus", "4.1.3"))

prepend_path("MODULEPATH", pathJoin("/work/noaa/global/glopara/git/prepobs/feature-GFSv17_com_reorg/modulefiles"))
load(pathJoin("prepobs", "1.0.1"))

prepend_path("MODULEPATH", pathJoin("/work/noaa/global/glopara/git/Fit2Obs/v1.0.0/modulefiles"))
load(pathJoin("fit2obs", "1.0.0"))

-- Temporary until official hpc-stack is updated
--prepend_path("MODULEPATH", "/work2/noaa/global/wkolczyn/save/hpc-stack/modulefiles/stack")
--append_path("MODULEPATH", "/work2/noaa/global/wkolczyn/save/hpc-stack/modulefiles/stack")
--load(pathJoin("hpc", "1.2.0"))
--load(pathJoin("hpc-intel", "2018.4"))
--load(pathJoin("hpc-miniconda3", "4.6.14"))
--load(pathJoin("ufswm", "1.0.0"))
--load(pathJoin("gfs_workflow", "1.0.0"))
--load(pathJoin("met", "9.1"))
--load(pathJoin("metplus", "3.1"))

whatis("Description: GFS run environment")
