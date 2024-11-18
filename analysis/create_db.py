import psycopg2
import gdaltools
import wget
import frontmatter
import os

#find geojson resource urls
cwd = os.getcwd()
directory_path = os.path.join(cwd, "..", "_datasets")
datasets = []
for filename in os.listdir(directory_path):
	if len(datasets) >=5: 
		break
	filepath = os.path.join(directory_path, filename)
	if os.path.isfile(filepath):
		try:
			dataset = frontmatter.load(filepath)
			resources = dataset.metadata.get("resources")
			for resource in resources:
				if resource.get("format") == "GeoJSON":
					resource_name = resource.get("name")
					url = resource.get("url")
					downloaded_filename = f"working_files/{filename}-{resource_name}.geojson"
					wget.download(url)
					datasets.append(downloaded_filename)
					# TODO: figure out how to handle datasets w multiple geojsons
		except Exception as e:
			print(f"Error loading {filename}: {e}")

DB_NAME="postgres"
DB_PORT=5433
DB_USER="docker"
DB_PW="docker"
DB_HOST="localhost"

# connection establishment
pg_conn = psycopg2.connect(
	database=DB_NAME,
	user=DB_USER,
	password=DB_PW,
	host=DB_HOST,
	port=DB_PORT
)

pg_conn.autocommit = True  # Enable autocommit to allow dropping database
cursor = pg_conn.cursor()

try:
    cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    print("PostGIS extension enabled.")
except Exception as e:
    print(f"Error enabling PostGIS: {e}")


OGR_CONFIG =  {"PG_USE_COPY": "YES", "OGR_TRUNCATE": "NO"}

# ogr config
ogr = gdaltools.ogr2ogr()
ogr_conn = gdaltools.PgConnectionString(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PW)
ogr.set_output_mode(layer_mode=ogr.MODE_LAYER_OVERWRITE, data_source_mode=ogr.MODE_DS_CREATE_OR_UPDATE)
ogr.config_options = OGR_CONFIG

#census_tracts
ogr.set_input("Census_Tracts_2010.geojson")
ogr.set_output(ogr_conn, table_name="census_tracts", srs="EPSG:4326")
ogr.execute()

#street_poles
for url in datasets:
	ogr.set_input(url)
	ogr.set_output(ogr_conn, table_name="street_poles", srs="EPSG:4326")
	ogr.execute()


# Closing the connection
cursor.close()
pg_conn.close()
