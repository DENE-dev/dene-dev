#! /usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import json
import requests
import pandas
# URL/HTLM
from urllib.parse import quote as urlencode
from urllib.request import urlretrieve
import http.client as httplib 

from astropy import coordinates, units
from astropy.io import ascii
from astropy.table import Table

# Astrobject
try:
    from astrobject.instruments import panstarrs
    _HAS_ASTROBJECT = True
except ImportError:
    _HAS_ASTROBJECT = False
    
# ==================== #
#                      #
#  Catalogs            #
#                      #
# ==================== #
def ps1cone(ra,dec,radius,table="mean",release="dr1",format="csv",columns=None,
           baseurl="https://catalogs.mast.stsci.edu/api/v0.1/panstarrs", verbose=False,
           **kw):
    """Do a cone search of the PS1 catalog
    
    Parameters
    ----------
    ra (float): (degrees) J2000 Right Ascension
    dec (float): (degrees) J2000 Declination
    radius (float): (degrees) Search radius (<= 0.5 degrees)
    table (string): mean, stack, or detection
    release (string): dr1 or dr2
    format: csv, votable, json, dataframe
    columns: list of column names to include (None means use defaults)
    baseurl: base URL for the request
    verbose: print info about request
    **kw: other parameters (e.g., 'nDetections.min':2)
    """
    
    data = kw.copy()
    data['ra'] = ra
    data['dec'] = dec
    data['radius'] = radius
    return ps1search(table=table,release=release,format=format,columns=columns,
                    baseurl=baseurl, verbose=verbose, **data)


def ps1search(table="mean",release="dr1",format="dataframe",columns=None,
           baseurl="https://catalogs.mast.stsci.edu/api/v0.1/panstarrs",
           verbose=False,
           **kw):
    """Do a general search of the PS1 catalog (possibly without ra/dec/radius)
    
    Parameters
    ----------
    table (string): mean, stack, or detection
    release (string): dr1 or dr2
    format: csv, votable, json
    columns: list of column names to include (None means use defaults)
    baseurl: base URL for the request
    verbose: print info about request
    **kw: other parameters (e.g., 'nDetections.min':2).  Note this is required!
    """
    
    data = kw.copy()
    if not data:
        raise ValueError("You must specify some parameters for search")
    checklegal(table,release)
    if format not in ("csv","votable","json","dataframe"):
        raise ValueError("Bad value for format")
    if format == "dataframe":
        format = "csv"
        get_dataframe=True
    else:
        get_dataframe=False
    url = "{baseurl}/{release}/{table}.{format}".format(**locals())
    if columns:
        # check that column values are legal
        # create a dictionary to speed this up
        dcols = {}
        for col in ps1metadata(table,release)['name']:
            dcols[col.lower()] = 1
        badcols = []
        for col in columns:
            if col.lower().strip() not in dcols:
                badcols.append(col)
        if badcols:
            raise ValueError('Some columns not found in table: {}'.format(', '.join(badcols)))
        # two different ways to specify a list of column values in the API
        # data['columns'] = columns
        data['columns'] = '[{}]'.format(','.join(columns))

# either get or post works
#    r = requests.post(url, data=data)
    r = requests.get(url, params=data)

    if verbose:
        print(r.url)
    r.raise_for_status()
    # DataFrame or not ?
    if get_dataframe:
        try:
            return ascii.read(r.text).to_pandas()
        except:
            raise IOError("DataFrame conversion failed. Most likely nothing at %s"%url)
    
    if format == "json":
        return r.json()
    else:
        return r.text

def checklegal(table,release):
    """Checks if this combination of table and release is acceptable
    
    Raises a VelueError exception if there is problem
    """
    
    releaselist = ("dr1", "dr2")
    if release not in ("dr1","dr2"):
        raise ValueError("Bad value for release (must be one of {})".format(', '.join(releaselist)))
    if release=="dr1":
        tablelist = ("mean", "stack")
    else:
        tablelist = ("mean", "stack", "detection")
    if table not in tablelist:
        raise ValueError("Bad value for table (for {} must be one of {})".format(release, ", ".join(tablelist)))


def ps1metadata(table="mean",release="dr1",
           baseurl="https://catalogs.mast.stsci.edu/api/v0.1/panstarrs"):
    """Return metadata for the specified catalog and table
    
    Parameters
    ----------
    table (string): mean, stack, or detection
    release (string): dr1 or dr2
    baseurl: base URL for the request
    
    Returns an astropy table with columns name, type, description
    """
    
    checklegal(table,release)
    url = "{baseurl}/{release}/{table}/metadata".format(**locals())
    r = requests.get(url)
    r.raise_for_status()
    v = r.json()
    # convert to astropy table
    tab = Table(rows=[(x['name'],x['type'],x['description']) for x in v],
               names=('name','type','description'))
    return tab


def mastQuery(request):
    """Perform a MAST query.

    Parameters
    ----------
    request (dictionary): The MAST request json object

    Returns head,content where head is the response HTTP headers, and content is the returned data
    """
    import sys    
    server='mast.stsci.edu'

    # Grab Python Version
    version = ".".join(map(str, sys.version_info[:3]))

    # Create Http Header Variables
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain",
               "User-agent":"python-requests/"+version}

    # Encoding the request as a json string
    requestString = json.dumps(request)
    requestString = urlencode(requestString)
    
    # opening the https connection
    conn = httplib.HTTPSConnection(server)

    # Making the query
    conn.request("POST", "/api/v0/invoke", "request="+requestString, headers)

    # Getting the response
    resp = conn.getresponse()
    head = resp.getheaders()
    content = resp.read().decode('utf-8')

    # Close the https connection
    conn.close()

    return head,content


def resolve(name):
    """Get the RA and Dec for an object using the MAST name resolver
    
    Parameters
    ----------
    name (str): Name of object

    Returns RA, Dec tuple with position"""

    resolverRequest = {'service':'Mast.Name.Lookup',
                       'params':{'input':name,
                                 'format':'json'
                                },
                      }
    headers,resolvedObjectString = mastQuery(resolverRequest)
    resolvedObject = json.loads(resolvedObjectString)
    # The resolver returns a variety of information about the resolved object, 
    # however for our purposes all we need are the RA and Dec
    try:
        objRa = resolvedObject['resolvedCoordinate'][0]['ra']
        objDec = resolvedObject['resolvedCoordinate'][0]['decl']
    except IndexError as e:
        raise ValueError("Unknown object '{}'".format(name))
    return (objRa, objDec)


# ==================== #
#                      #
#  Images              #
#                      #
# ==================== #
def query_panstarrs_metadata(ra, dec, size=240, filters="grizy", type="stack"):
    
    """ Query ps1filenames.py service to get a list of images
    
    Parameters
    ----------
    ra, dec: [floats] 
        position in degrees
    size: [float] 
        image size in pixels (0.25 arcsec/pixel)
    filters: [strings]
        string with filters to include
        
    Returns
    --------
    Table (a table with the results)
    """
    

    service = "https://ps1images.stsci.edu/cgi-bin/ps1filenames.py"
    url = ("{service}?ra={ra}&dec={dec}&size={size}&type={type}&format=fits"
           "&filters={filters}").format(**locals())
    d_ = pandas.read_csv(url, sep=" ")
    d_["basename"] = d_.pop("shortname")
    d_["baseurl"]  = d_.pop("filename")
    d_["project"]  = "ps1"
    d_["filters"] = d_["filter"]
    return d_

def _ps_pstodata_(dataframe, directory):
    """ """
    return [directory+"%s_"%target_+"%s"%basename_
                for target_,basename_ in zip(dataframe["name"],dataframe["basename"])]
    
def _ps_pstourl_(dataframe, format="fits", size=240, type="stack", output_size=None):
    """ Get URL for images in the table
    
    Parameters
    ----------
    format: [string] 
        data format (options are "jpg", "png" or "fits")
                
    Returns
    -------
    String (a string with the URL)
    """
    if format not in ["jpg","png","fits"]:
        raise ValueError("format must be one of jpg, png, fits (%s given)"%format)
    
    url = ("https://ps1images.stsci.edu/cgi-bin/fitscut.cgi?"
           "ra={ra}&dec={dec}&size={size}&type={type}&format={format}").format(
               **{"ra":dataframe["ra"].values[0],"dec":dataframe["dec"].values[0],
                      "size":size, "type":type,"format":format})
    if output_size:
        url = url + "&output_size={}".format(output_size)
        
    # sort filters from red to blue
    urlbase = url + "&red="
    return [urlbase+filename for filename in dataframe['baseurl'].values]

def get_ps_url(ra, dec, size=240, output_size=None, filters="grizy", type="stack", format="fits"):#, color=False):
    
    """ Get URL for images in the table
    
    Parameters
    ----------
    ra, dec: [floats] 
        position in degrees

    size: [float] 
        image size in pixels (0.25 arcsec/pixel)

    filters: [strings]
        string with filters to include

    format: [string] 
        data format (options are "jpg", "png" or "fits")
        
    color: [bool]
        if True, creates a color image (only for jpg or png format).
        Default is return a list of URLs for single-filter grayscale images.
        
    Returns
    -------
    String (a string with the URL)
    """
        
    df = query_panstarrs_metadata(ra, dec, size=size, type=type, filters=filters)
    return _ps_pstourl_(df, output_size=output_size, size=size, type=type, format=format)#, color=color)


def download_single_url(url, fileout=None, mkdir=True,
                        overwrite=False, verbose=True, chunk=1024, **kwargs):
    """ Download the url target using requests.get.
    the data is returned (if fileout is None) or stored in `fileout`
    Pa
    """
    import requests
    import os
    if (fileout is not None and fileout not in ["BytesIO", "StringIO"]) and not overwrite and os.path.isfile( fileout ):
        if verbose:
            print("%s already exists: skipped"%fileout)
        return
    else:
        if verbose and fileout:
            print("downloading %s"%fileout)
    
    request_fnc = "get" if not "data" in kwargs else "post"
    response = getattr(requests,request_fnc)(url, **kwargs)
    if response.status_code == 200:
        if fileout in ["BytesIO", "StringIO"]:
            import io
            return getattr(io, fileout)(response.content)
        
        with open(fileout, 'wb') as f:
            for data in response.iter_content(chunk):
                f.write(data)
    else:
        print("Issue downloading")
        print("response.status_code: ", response.status_code)



# ==================== #
#                      #
#  Class PS1 Object    #
#                      #
# ==================== #

PS1STACKCOL= ["objInfoFlag","objID","objName","qualityFlag",
                      "raStack","decStack","raStackErr","decStackErr",
                      "raMean","decMean","raMeanErr","decMeanErr",
                      "ng","nr","ni","nz","ny",
                      ]
PS1STACKCOL += ["%sPSFMag"%f for f in   ["g","r","i","z","y"]]
PS1STACKCOL += ["%sPSFMagErr"%f for f in ["g","r","i","z","y"]]
PS1STACKCOL += ["%sKronMag"%f for f in  ["g","r","i","z","y"]]
PS1STACKCOL += ["%sKronMagErr"%f for f in ["g","r","i","z","y"]]
PS1STACKCOL += ["%sApMag"%f for f in    ["g","r","i","z","y"]]
PS1STACKCOL += ["%sApMagErr"%f for f in ["g","r","i","z","y"]]

class _EllipseObject_( object ):
    """ """
    def _get_sorted_id_(self, radec=None, relative=True):
        """ """
        raise NotImplementedError("You Class must define this, It must ")

    def get_id_ellipse(self, id_, **kwargs):
        """ """
        raise NotImplementedError("You Class must define this, It must ")
            
    def derive_dist(self, radec=None, relative=True, update=True):
        """ """
        if radec is not None:
            self.set_radec(ra,dec)
            
        id_, dist =  self._get_sorted_id_(relative=relative)
        if update:
            which = "relative" if relative else "angular"
            self.nearest_id[which] = {"id":id_,"dist":dist}
            
        return id_,dist

    def set_radec(self,ra,dec):
        """ """
        self.radec= ra,dec

    # --------- #
    #  GETTER   #
    # --------- #
    def get_nearest(self, nnearest=1,  relative=True, update=True, rederive=False):
        """ """
        # Already loaded ?
        which = "relative" if relative else "angular"
        if  self.nearest_id[which]["id"] is None or rederive:
            id_, dist = self.derive_dist(relative=relative, update=update)
        else:
            id_, dist = self.nearest_id[which]["id"][:nnearest],self.nearest_id[which]["dist"][:nnearest]
            
        return id_[:nnearest], dist[:nnearest]

        
        
        return id_[:nnearest], dist[:nnearest]
    
    def get_nearest_distance(self, nnearest=1, relative=True, update=True, rederive=False):
        """ """
        lwargs = locals()
        _ = lwargs.pop("self")
        return self.get_nearest(**lwargs)[1]
    
    def get_nearest_id(self, nnearest=1, relative=True, update=True, rederive=False):
        """ """
        lwargs = locals()
        _ = lwargs.pop("self")
        return self.get_nearest(**lwargs)[0]

    
    def get_nearest_ellipse(self, nnearest=1, relative=True):
        """ """
        return self.get_id_ellipse(
                self.get_nearest_id( nnearest=nnearest, relative=relative)
                )
    # ================ #
    #   Properties     #
    # ================ #
    @property
    def nearest_id(self):
        """ """
        if not hasattr(self,"_nearest_id"):
            self._nearest_id = {"angular": {"id":None,"dist":None},
                                   "relative":{"id":None,"dist":None},
                                  }
        return self._nearest_id


    
class PSDataCatalog( _EllipseObject_ ):
    """ """
    def __init__(self, dataframe, band, which, radec=None):
        """ """
        self.data = dataframe
        self.band = band
        self.which = which
        self.set_radec(*radec)

    def _get_sorted_id_(self, relative=True, max_dist=None, scaleup=3):
        """ """
        ra,dec = self.radec
        skyradec = coordinates.SkyCoord(*self.data[["Ra","Dec"]].values.T, unit="deg") # in cat
        coord    = coordinates.SkyCoord(ra, dec , unit="deg") # to be compared with
        ang_dist = skyradec.separation(coord).to('arcsec')
        # Nearest in angular distance
        id_sortdist = self.data.index[np.argsort(ang_dist)]
        
        if max_dist is not None:
            id_sortdist = id_sortdist[ang_dist[np.argsort(ang_dist)]<max_dist]

        if not relative:
            return id_sortdist, ang_dist[np.argsort(ang_dist)].value

        
        # Now measure the relative distances
        
        # *Caution here* a, and b are in ARCSEC, x and y in degree
        # - Ellipse parameters
        x,y,a,b,t = np.asarray(self.get_id_ellipse(id_sortdist))
        dx,dy = np.asarray([ra-x,dec-y])*units.deg.to("arcsec")# Ra Dec are in deg
        t = t*-1 # to follow the def below
        a,b = a*scaleup,b*scaleup
        cxx = np.cos(t)**2/a**2 +  np.sin(t)**2/b**2
        cyy = np.sin(t)**2/a**2 +  np.cos(t)**2/b**2
        cxy = 2*np.cos(t)*np.sin(t)*(1/a**2 - 1/b**2)
        # - Measuring relative distances
        dist_relative = np.sqrt( cxx*dx**2 + cyy*dy**2 + cxy * (dx*dy) )
        relat_sort_id = np.argsort(dist_relative)
        return id_sortdist[relat_sort_id], dist_relative[relat_sort_id]
    

    def get_id_ellipse(self, id_=None,  **kwargs):
        """ get the ellipse parameters for the given id

        Parameters
        ----------
        id_: [int or list of]
            ID for which you want the ellipse.

        Returns
        -------
        x,y,a,b,t
        Info: x,y: centroids ; a,b: major,minos axis ; t: angle [in rad] 
        """
        df = self.data.loc[id_] if id_ is not None else self.data
        x,y,a, ab, tdeg = df[["Ra","Dec", "Radius","Ab","Phi"]].values.T
        b   = a*ab
        t   = tdeg*np.pi/180 # given in deg (-1 to keep the same def as sep)
        ellipse_param = np.asarray([x,y,a,b,t])
        return ellipse_param.T[0] if len(df) ==1 else ellipse_param
    
    
class SEPCatalog( _EllipseObject_ ):
    """ """
    def __init__(self, sepobjects, band, radec=None):
        """ """
        self.sepobjects = sepobjects
        self.band = band
        self.set_radec(*radec)
        
    def _get_sorted_id_(self, relative=True, **kwargs):
        """ Get the sort data entry 
        
        Parameters
        ----------
        radec: [float,float]
            Coordinate [in deg if wcs_coords, else in pixels]
            
        wcs_coords: [bool] -optional-
            Are the coordinates RA, Dec [True] or pixels [False]?
        
        max_dist: [float/None] -optional-
            Maximum matching distance.
            - None: no maximum
            - float: maximum distance [in arcsec]

        relative: [bool] -optional-
            Shall the distance be compared in angular distance [False]
            or in galactic elliptical distance [True]

        Parameters
        ----------
        list of id
        """
        id_,dist_= self.sepobjects.get_nearest(*self.radec, nnearest=None,
                                            relative=relative, **kwargs)
        if relative:
            return id_, dist_
        return id_, dist_.value
    
    def get_id_ellipse(self, id_=None,**kwargs):
        """ get the ellipse parameters for the given id

        Parameters
        ----------
        id_: [int or list of]
            ID for which you want the ellipse.

        Returns
        -------
        x,y,a,b,t
        Info: x,y: centroids ; a,b: major,minos axis ; t: angle [in rad] 
        """
        return self.sepobjects.get_ellipse_values(id_,**kwargs)

class PS1Target(object):
    """ """
    def __init__(self, dataframe, radec=None):
        """ """
        if radec is not None:
            self.set_coordinate(*radec)
        self.set_catdata(dataframe)
        
    @classmethod
    def from_objid(cls, objid):
        """ """
        dataframe = ps1search(table="stack",release='dr2', format="dataframe",
                          columns=PS1STACKCOL,
                          verbose=False,objid=objid)
        radec = dataframe[["raMean","decMean"]].values[0]
        return cls(dataframe, radec=radec)
    
    @classmethod
    def from_coord(cls, ra, dec, rdeg=0.02, load_catalog=True):
        """ """
        skycoord = ra,dec
        if load_catalog:
            dataframe = ps1cone(ra, dec, rdeg, table="stack",release='dr2', format="dataframe",
                          columns=PS1STACKCOL,
                          verbose=False)
        else:
            dataframe=None
        return cls(dataframe, skycoord)

    # ============= #
    #  Method       #
    # ============= #
    def set_catdata(self, dataframe):
        """ """
        self._catdata = dataframe

    def set_coordinate(self, ra,dec):
        """ """
        self._skycoord = coordinates.SkyCoord(ra,dec, unit="deg")

    def set_sep(self, band="r"):
        """ """
        self._sep = SEPCatalog(self.imgcutout[band].sepobjects, band, radec=[self.coordinate.ra.deg,self.coordinate.dec.deg])

    def set_galcat(self, band="r", which="DeV"):
        """ """
        # DEFAULT CATALOG
        if which in ["default", "galcat"]:
            which = "DeV" if self.galcat is None else self.galcat.which
            
        if not self._extended_cat_set:
            self.download_extended_catalog()

        keys = [k for k in self.catdata.keys() if band+which in k]
        df = self.catdata[keys].copy()
        df = df.rename(columns={k:k.split(which)[-1] for k in df.columns})
        self._galcat = PSDataCatalog(df[df["Mag"] != -999], band, which=which, radec=[self.coordinate.ra.deg,self.coordinate.dec.deg])
        
    # // Setting checkup
    def _source_checkup_(self, band, source):
        """ """
        if source == "sep":
            self._sep_checkup_(band)
            return "sep"
        if source in ["galcat", "DeV", "Ser"]:
            self._galcat_checkup_(band, source)
            return "galcat"
        raise ValueError("source should be 'sep','galcat' or, to specify the galcat, 'DeV' or 'Ser'. %s given"%source)
    
    def _sep_checkup_(self, band):
        """ """
        if self.sep is None or (band is not None and self.sep.band != band):
            self.set_sep(band)
            
    def _galcat_checkup_(self, band, which):
        if self.galcat is None or (band is not None and self.galcat.band != band) or (which !="galcat" and self.galcat.which != which):
            self.set_galcat(band, which)

    
    #def dist_from(self, ra, dec, elliptical=True):
    #    """ """
    #    skypos = coordinates.SkyCoord(ra,dec, unit="deg")
    #    if not elliptical:
    #        return self.coordinate.separation(skypos)
        
    # ------- #
    # LOADER  #
    # ------- #
    def download_catalog(self, update=True, rdeg=0.02 ):
        """ """
        dataframe = ps1cone(self.coordinate.ra.deg, self.coordinate.dec.deg,
                                rdeg,
                                table="stack",release='dr2', format="dataframe",
                                columns=PS1STACKCOL,
                                verbose=False)
        if update:
            self.set_catdata(dataframe)
        else:
            return dataframe

    def download_extended_catalog(self, merge=True):
        """ Dowloads smaller catalog source from PS:
        https://outerspace.stsci.edu/display/PANSTARRS/PS1+Source+extraction+and+catalogs
        
        Here merging:
        StackModelFitDeV: 
            Contains the de Vaucouleurs fit parameters for stack
            detections brighter than some limit (is this a S/N cut or a mag limit?) 
            outside the galactic plane. 
            All filters are matched into a single row. 
            Given are mag, radius, axial ratio, position angle, RA, Dec, chisq of fit.
        
        StackModelFitSer: 
            Contains the Sersic fit parameters for stack 
            detections brighter than magnitude 21.5 outside the galactic plane. 
            All filters are matched into a single row. 
            Given are mag, radius, axial ratio, Sersic index, position angle, RA, Dec, chisq of fit.


        """
        if self.catdata is None:
            self.download_catalog(update=True)
        objid = ",".join(["%s"%s for s in self.catdata["objID"].values])
        
        from astroquery.utils.tap.core import TapPlus
        tap_service = TapPlus(url="http://vao.stsci.edu/PS1DR2/tapservice.aspx")
        
        job = tap_service.launch_job_async("""
        SELECT *
        FROM dbo.StackModelFitDeV AS dev
        LEFT JOIN dbo.StackModelFitSer AS ser
            ON dev.objID = ser.objID
        WHERE
        dev.objID IN ({})
        """.format(objid))
        results = job.get_results().to_pandas()
        
        if merge:
            self._catdata = pandas.merge(self.catdata, results, on="objID")
            self._is_extended_cat_set = True
        else:
            self._is_extended_cat_set = False
            return results

    def download_cutout(self, filters=["g","r","i","z","y"], size=240, run_sep=True, load_weight=False, background=0, target=None):
        """ """
        if not _HAS_ASTROBJECT:
            raise ImportError("This method needs astrobject. pip install astropbject")
        
        from astrobject import get_target
        filters = np.atleast_1d(filters)
        self._url = get_ps_url(self.coordinate.ra.deg, self.coordinate.dec.deg, filters="".join(filters), size=size, type="stack")
        if load_weight:
            _wt_url = get_ps_url(self.coordinate.ra.deg, self.coordinate.dec.deg, filters="".join(filters), size=size, type="stack.wt")
        self._cutout = {}
        for ii, url in enumerate(self._url):
            inst_ = panstarrs.PanSTARRS(download_single_url(url, fileout="BytesIO"),
                                        weightfilename=download_single_url(_wt_url[ii], fileout="BytesIO") if load_weight else None,
                                        background=background, astrotarget=target)
            self._cutout[inst_.bandname.split(".")[-1]] = inst_
        
        if self.coordinate is not None:
            for img in self._cutout.values():
                if not img.has_target():
                    img.set_target(get_target(ra=self.coordinate.ra.deg,
                                              dec=self.coordinate.dec.deg
                                              ))
        if run_sep:
            self.sep_extract("*")
            self.set_sep(filters[0])
        
    def sep_extract(self, filters="*", **kwargs):
        """ """
        if filters is None or filters in ["all", "*"]:
            filters = self.imgcutout.keys()
        for f in filters:
            self.imgcutout[f].sep_extract(**kwargs)
        
    # ------- #
    # GETTER  #
    # ------- #
    def _pps_to_format_(self, pps, format_):
        """ """
        if format_ == "photopoint":
            return pps
        if format_ == "flux":
            return {b:[pp.flux, np.sqrt(pp.var)] for b,pp in pps.items()}
        if format_ == "mag":
            return {b:[pp.mag, pp.mag_err] for b,pp in pps.items()}
        
    # // Photometry
    def get_local_photometry(self, radius, runits="arcsec", filters=["g","r","i","z","y"],
                                 format="photopoint", **kwargs):
        """ """
        pps = {b:self.imgcutout[b].get_target_photopoint(radius, runits, **kwargs)
                   for b in np.atleast_1d(filters)}
        
        return self._pps_to_format_(pps, format)
            
    def get_global_photometry(self, id_, source="sep", 
                                  filters=["g","r","i","z","y"],
                                 format="photopoint", **kwargs):
        """ Get the global photometry of the given id's source
        
        Parameters
        ----------
        id_: [int or list-of]
            id_ could be:
            - `sepid` if source='sep': the global magnitude will be the 
                    integrated magnitude given the sep ellipses (R=3)
            - `galcatid` if source='galcat/DeV/Ser`.
            
        source: [string] -optional-
            What is the source of the magnitude:
            sep.{filter} or galcat/DeV/Ser
            - If you use source=sep, you need to specify the
              band used for the ellipse (images are aligned).
              e.g.: get the filters mag inside the sep ellipse from band 'r':
                    -> source='sep.r'
            

        filters: [string or list of] -optional-
            Which PS1 filters do you want data for?

        format: [string] -optional-
            output format: photopoint/flux/mag

        Returns
        -------
        dict | {filter: format}
        """
        if source in ["galcat","DeV","Ser"]:
            if source == "galcat":
                source = self.galcat.which
            # - part of the DataFrame to consider
            df = self.catdata.loc[id_]
            mags = {f:np.asarray(df[["%s%sMag"%(f,source),"%s%sMagErr"%(f,source)]].values.T,
                                     dtype="float").tolist()
                        for f in filters}
            if format == "mag" and not _HAS_ASTROBJECT:
                return mags
            elif not _HAS_ASTROBJECT:
                raise ImportError("This method needs astrobject (or set format='mag' for non-sep source. pip install astropbject")
            
            from astrobject import photometry    
            pps = {f:photometry.PhotoPoint.from_mag(*mags[f],
                                            lbda=panstarrs.PANSTARRS_INFO["ps1.%s"%f]["lbda"],
                                                **kwargs)
                       for f in filters}
            
        elif "sep" in source:
            try:
                _, band = source.split(".")
            except:
                raise ValueError("When using sep you need to specify the ellipse band source as sep.BAND e.g. source='sep.r'")
            self._sep_checkup_(band)
            x,y,a,b,t = self.sep.get_id_ellipse(id_)
            scaleup = kwargs.pop("scaleup",3) # R=3 as in Sextractor doc
            pps = {f:self.imgcutout[f].get_photopoint(x,y, radius=scaleup, runits="pixels",
                                                          ellipse_args=dict(a=a, b=b, theta=t),
                                                          aptype="ellipse", **kwargs)
                       for f in ["g","r","i","z","y"]}
        else:
            raise ValueError("Could not parse the inout source %s. source should be sep or galcat/DeV/Ser "%source)
        
        return self._pps_to_format_(pps, format)

    # //
    # // Catalog and SEP
    # //
    def match_sepcat(self, band="r", distmatch=2*units.arcsec):
        """ """
        if self.sep is None or self.sep.band != band:
            self.set_sep(band)
            
        sepid  = coordinates.SkyCoord(*self.sep.sepobjects.pixel_to_coords(*self.sep.get_id_ellipse()[:2]).T, unit="deg")
        skycat = coordinates.SkyCoord(*self.catdata[["raMean","decMean"]].values.T, unit="deg")
        
        idxcatalogue, idxsepobjects, d2d, d3d = sepid.search_around_sky(skycat, distmatch)
        self.catdata.loc[idxcatalogue,"sepid"] = idxsepobjects
        self.catdata.loc[idxcatalogue,"sepdist"] = d2d.arcsec
        
    def get_sepid_catdata(self, sepid):
        """ 
        acceptance: [float] -optional-
            Acceptance size for matching, in arcsec
            
        """
        if self.catdata is None:
            self.download_catalog()
        if "sepid" not in self.catdata:
            self.match_sepcat()

        return self.catdata[self.catdata["sepid"].isin(np.atleast_1d(sepid))]
    
    #
    # Nearest Source
    #

    def get_nearest(self, nnearest=1, band="r", relative=True,
                                 source="sep", inpixel=None, **kwargs):
        """ """
        source_ = self._source_checkup_(band, source)
        id_, dist_  = getattr(self,source_).get_nearest(nnearest=nnearest, relative=relative,
                                                        **kwargs)
        if inpixel is None or relative:
            return id_, dist_
        
        if source_ == "galcat" and inpixel:
            dist_  = dist_ / self.imgcutout[band].pixel_size_arcsec.value
        if source_ == "sep" and not inpixel:
            dist_ = dist_ * self.imgcutout[band].pixel_size_arcsec.value
            
        return id_, dist_
    
    def get_nearest_sepid(self, nnearest=1, band="r",  relative=True, **kwargs):
        """ """
        self._sep_checkup_(band)
        return self.sep.get_nearest_id(nnearest=nnearest, relative=relative,**kwargs)

    def get_nearest_galcatid(self, source="galcat", nnearest=1, band="r", relative=True, **kwargs):
        """ """
        self._galcat_checkup_(band, source)
        return self.galcat.get_nearest_id(nnearest=nnearest, relative=relative,**kwargs)
        
    #
    # Nearest Derived
    #
    def get_nearest_distance(self, nnearest=1, band="r", relative=True,
                                 source="sep", inpixel=None, **kwargs):
        """ """
        return self.get_nearest( nnearest=nnearest, band=band, relative=relative,
                                 source=source, inpixel=inpixel, **kwargs)[1]
        
    
    def get_nearest_catdata(self, nnearest=1, band="r", relative=True, source="sep", **kwargs):
        """ """
        source_ = self._source_checkup_(band, source)
        id_ = getattr(self,'get_nearest_%sid'%source_)(band=band, nnearest=nnearest,
                                                        relative=relative, **kwargs)
        if source in ["sep"]:
            return self.get_sepid_catdata(id_)
        else:
            return self.catdata.loc[id_]

    def get_id_ellipse(self, id_, band="r", source="sep", inpixel=None, **kwargs):
        """ """
        source_ = self._source_checkup_(band, source)
        ells = getattr(self,source_).get_id_ellipse(id_,  **kwargs)
        
        if inpixel is None:
            return ells
        
        if source_ == "galcat" and inpixel:
            img = self.imgcutout[band]
            x,y = img.coords_to_pixel(ells[0],ells[1]).T
            a,b = ells[2:4]/ img.pixel_size_arcsec.value
            ells = np.asarray([x,y,a,b,ells[-1]])
        if source_ == "sep" and not inpixel:
            img = self.imgcutout[band]
            x,y = img.pixel_to_coords(ells[0],ells[1]).T
            a,b = ells[2:4] * img.pixel_size_arcsec.value
            ells = np.asarray([x,y,a,b,ells[-1]])
            
        return ells
    
    def get_nearest_ellipse(self, nnearest=1, band="r", relative=True,
                                source="sep", inpixel=None):
        """ """
        source_ = self._source_checkup_(band, source)
        nearestid = self.get_nearest( nnearest=nnearest, band=band,
                                     relative=relative, source=source, inpixel=None)[0]
        return self.get_id_ellipse(nearestid, band=band, source=source, inpixel=inpixel)
    
    def get_nearest_ps1target(self, nnearest=1, band="r", relative=True, source="sep"):
        """ """
        dataframe_nearest = self.get_nearest_catdata(nnearest=nnearest,band=band,relative=relative,
                                                         source=source)
        if len(dataframe_nearest) ==0:
            warnings.warn("No near target found")
            return None
        if nnearest == 1:
            return self.__class__(dataframe_nearest)
        else:
            return [self.__class__(df) for df in dataframe_nearest.iterrows()]
    
    # -------- #
    # PLOTTER  #
    # -------- #
    def show(self, ax=None, band="r", show_coord=None,
                 source='sep', ellipse=True, ell_color="k",
                 coord_color="C1",scaleup=3,**kwargs):
        """ """
        if self.has_imgcutout():
            img = self.imgcutout[band]
            ax = img.show(ax=ax,show_sepobjects=False)['ax']
            inpixel=True
            has_img=True
        elif ax is None:
            import matplotlib.pyplot as mpl
            fig = mpl.figure(figsize=[5,5])
            ax = fig.add_subplot(111)
            inpixel=False
            has_img=False

        # - RA,Dec or x,y
        if inpixel:
            x,y = img.coords_to_pixel(self.coordinate.ra.deg, self.coordinate.dec.deg)
        else:
            x,y = self.coordinate.ra.deg, self.coordinate.dec.deg
            
        ax.scatter(x,y, **{**dict(marker="+", color='k', s=100),**kwargs})
        
        if ellipse:
            from matplotlib.patches import Ellipse
            x,y,a,b,t = self.get_nearest_ellipse(source=source, inpixel=inpixel)
            ax.add_patch(Ellipse([x,y],2*a*scaleup,2*b*scaleup,t*units.rad.to("deg"), 
                     facecolor="None", edgecolor=ell_color, lw=2))            
            if not has_img:
                ax.scatter(x,y, marker=".", color=ell_color)
                ax.set_xlim(x-3*a,x+3*a)
                ax.set_ylim(y-3*a,y+3*a)
                
        if show_coord is not None:
            if inpixel:
                x,y = img.coords_to_pixel(*show_coord)
            else:
                x,y, = show_coord
            
            ax.scatter(x,y, marker="x", color=pt_color, s=100)

        return ax.figure
    # ============= #
    #  Properties   #
    # ============= #
    @property
    def coordinate(self):
        """ """
        if not hasattr(self,"_skycoord") or self._skycoord is None:
            self.set_coordinate(*self.catdata[["raStack","decStack"]].values[0])
        return self._skycoord

    @property
    def ellipse(self):
        """ """
        if not hasattr(self,"_ellipse") or self._ellipse is None:
            self.derive_ellipse()
        return self._ellipse
        
    @property
    def catdata(self):
        """ """
        if not hasattr(self,"_catdata"):
            self._catdata = None
        return self._catdata

    @property
    def _extended_cat_set(self):
        """ """
        if not hasattr(self,"_is_extended_cat_set"):
            self._is_extended_cat_set = False
        return self._is_extended_cat_set
    
    @property
    def sep(self):
        """ """
        if not hasattr(self,"_sep"):
            self._sep = None
        return self._sep

    @property
    def galcat(self):
        """ """
        if not hasattr(self,"_galcat"):
            self._galcat = None
        return self._galcat
    
    # - Images
    @property
    def imgcutout(self):
        """ """
        if not self.has_imgcutout():
            raise AttributeError("No cutout loaded yet. Run self.download_cutout()")
        
        return self._cutout
    
    def has_imgcutout(self):
        """ Test if at least 1 curtout loaded. """
        return hasattr(self,"_cutout")
