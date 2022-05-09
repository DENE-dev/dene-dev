import logging
import sys
import argparse
import pathlib
import os 
import psycopg2 #pip3 install psycopg2
import tempfile
from lib import ogr2ogr #pip3 install GDAL>2.4.0
from geoserver.catalog import Catalog #pip3 install geoserver-restconfig

log = logging.getLogger("ogr2ps2gs")
log.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)


def existTable(cur, table_name):
    """Check to see if a table 

    :param cur: PostGIS database cursor
    :type cur: psycopg2.extensions.cursor
    :param table_name: PostGIS database table name
    :type table_name: str

    :return: If the table already exists in the database
    :rtype: bool
    """

    sql = cur.mogrify("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name=%s)", (table_name,))

    log.debug("Sending SQL: %s" % sql)    
    cur.execute(sql)

    return cur.fetchone()[0]

def dropTable(cur, table_name):
    """Check to see if a table 

    :param cur: PostGIS database cursor
    :type cur: psycopg2.extensions.cursor
    :param table_name: PostGIS database table name
    :type table_name: str

    :rtype: None
    """

    log.warning("The following command is susceptible to SQL injection.")

    #psycopg2 does not correctly/safely mogrify the following command
    #consider using a regular expression to check for safety
    #sql = cur.mogrify("DROP TABLE IF EXISTS %s", (table_name,))

    sql = "DROP TABLE IF EXISTS \"%s\"" % table_name

    log.debug("Sending SQL: %s" % sql)
    cur.execute(sql)

def insertVector(cur, in_path,table_name):
    """Insert vector data into a PostGIS database

    :param cur: PostGIS database cursor
    :type cur: psycopg2.extensions.cursor
    :param in_path: Path to vector data
    :type in_path: str
    :param table_name: PostGIS database table name
    :type table_name: str

    :rtype: None
    """
    
    log.debug("Converting file %s to PostgreSQL" % in_path)
    tmp = tempfile.NamedTemporaryFile()
    try:
        ogr2ogr.main(["","-f", "PGDump", tmp.name, in_path, "-a_srs", "EPSG:4326", "-nln", table_name, "-lco", "GEOM_TYPE=geography"])
    except RuntimeError as e:
        log.error("GDAL failed to convert %s" % in_path)
        raise e

    log.debug("Attempting to create table %s" % table_name)
    try:
        cur.execute(tmp.read())
    except psycopg2.errors.DuplicateTable as e:
        log.error("Table %s already exists" % table_name)
        raise psycopg2.errors.DuplicateTable("%s table already exists" % table_name)

def publishVector(cur, table_name, postgis_connection_string, cat):
##    log.debug("Adding table read premisison to user %s" % geoserver_user)
##    try:
##        sql = cur.mogrify("GRANT SELECT ON TABLE %s TO %s" % (table_name, geoserver_user,))
##        log.debug("Sending SQL: %s" % sql)
##        cur.execute(sql)
##        
##    except psycopg2.errors.UndefinedTable as e:
##        log.error("Table %s does not exist" % table_name)
##        raise e

    log.debug("Creating workspace")
    ws = cat.create_workspace('newWorkspaceName','newWorkspaceUri')

    log.debug("Create PostGIS store")
    ds = cat.create_datastore(newDatastoreName,newWorkspaceName)
    _, dbname, _, user, _, host, _, password, _, sslmode = postgis_connection_string.split("=")
    port = "5432"
    dbtype='postgis'
    schema="public"
    ds.connection_parameters.update(host=host, port=port, database=dbname, user=user, password=password, dbtype=dbtype, schema=schema)
    cat.save(ds)    

    log.debug("Add layer")
    ft = cat.publish_featuretype('newLayerName', ds, 'EPSG:4326', srs='EPSG:4326')
    cat.save(ft)

def construct_parser():
    parser = argparse.ArgumentParser(description="Store vector data from a file in a PostGIS database and publish it to GeoServer")
    parser.add_argument("-v", "--version", help="show program version", action="store_true")
    parser.add_argument("-l", "--log", help="Log activity to the specified file", action="store_true")
    parser.add_argument("-dt", "--droptable", help="Drop table if it already exists", action="store_true")
    parser.add_argument("name", help="The table name to use for the vector data in PostGIS", type=str)
    parser.add_argument("path", help="Vector data to store in PostGIS and publish to GeoServer", type=pathlib.Path)

    return parser

if __name__ == "__main__":
    args = construct_parser().parse_args()

    in_path = os.path.abspath(str(args.path))
    table_name = args.name
    
    if args.version:
        log.info("Version number 0.0.0")
        
    try:
        log.debug("Loading default credentials")
        cwd = os.path.dirname(os.path.realpath(__file__))
        secure_path = os.path.join(os.path.dirname(cwd), "secure")
        pyscopg2_connection_string = open(os.path.join(secure_path, "private_psycopg2_connection_string.txt")).read()
        gsconfig_url = open(os.path.join(secure_path, "private_gsconfig_local_url.txt")).read()
        gsconfig_username = open(os.path.join(secure_path, "private_gsconfig_username.txt")).read()
        gsconfig_password = open(os.path.join(secure_path, "private_gsconfig_key.txt")).read()

    except FileNotFoundError as e:
        log.error("Missing default credentials")
        log.error(str(e))

    log.info("Connecting to PostgreSQL")        
    conn = psycopg2.connect(pyscopg2_connection_string)
    conn.autocommit = True
    cur = conn.cursor()

    log.info("Connecting to GeoServer")
    cat = Catalog(gsconfig_url, gsconfig_username, gsconfig_password)
    

    if args.droptable:
        log.info("Dropping table %s if it exists" % table_name)
        dropTable(cur, table_name)

    log.info("Pushing data to PostgreSQL")
    insertVector(cur, in_path, table_name)

    log.info("Pushing data to GeoServer")
    publishVector(cur, table_name, pyscopg2_connection_string, cat)

    log.debug("Commiting changes to database and closing connection")
    cur.close()
    conn.commit()
    conn.close()

