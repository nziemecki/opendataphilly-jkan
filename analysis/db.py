from dotenv import load_dotenv
import os
import psycopg2
import subprocess


class DB:
    def __init__(self):
        load_dotenv()
        self.params = {
            "DB_NAME": os.getenv("DB_NAME"),
            "DB_PORT": os.getenv("DB_PORT"),
            "DB_USER": os.getenv("DB_USER"),
            "DB_PW": os.getenv("DB_PW"),
            "DB_HOST": os.getenv("DB_HOST"),
        }

    def connect(self):
        self.connection = psycopg2.connect(
            database=self.params.get('DB_NAME'),
            user=self.params.get('DB_USER'),
            password=self.params.get('DB_PW'),
            host=self.params.get('DB_HOST'),
            port=self.params.get('DB_PORT'),
        )

        self.connection.autocommit = (
            True  # Enable autocommit to allow dropping database
        )
        cursor = self.connection.cursor()

        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            print("PostGIS extension enabled.")
        except Exception as e:
            print(f"Error enabling PostGIS: {e}")

        cursor.close()

    def close(self):
        if self.connection:
            self.connection.close()

    def prepare_datasets_table(self, table_name):
        cursor = self.connection.cursor()
        cursor.execute(f"""DROP TABLE IF EXISTS "{table_name}";""")
        cursor.execute(
            f"""
                CREATE TABLE "{table_name}" (
                    id SERIAL PRIMARY KEY,
                    resource_name VARCHAR(255),
                    wkb_geometry GEOMETRY (geometry, 4326)
                )
            """
        )
        cursor.close()

    def derive_census_tracts_from_datasets(self, table_name):
        cursor = self.connection.cursor()
        query = f"""
            SELECT DISTINCT c.GEOID10
            FROM "{table_name}" d
            JOIN census_tracts c
            ON st_intersects(d.wkb_geometry, c.wkb_geometry)
            ORDER BY c.GEOID10
        """
        query_with_csv_export = "COPY ({0}) TO STDOUT WITH CSV HEADER".format(query)
        csv_file = open("working_files/test.csv", "w")
        cursor.copy_expert(query_with_csv_export, csv_file)
        cursor.close()

    def import_census_tracts(self):
        subprocess.run(
            [
                "ogr2ogr",
                "-f",
                "PostgreSQL",
                f"PG:host={self.params.get('DB_HOST')} user={self.params.get('DB_USER')} dbname={self.params.get('DB_NAME')} password={self.params.get('DB_PW')} port={self.params.get('DB_PORT')}",
                "working_files/Census_Tracts_2010.geojson",
                "-nln",
                "census_tracts",
                "-t_srs", "EPSG:4326",
                "-overwrite"
            ]
        )

    def import_dataset(self, path, table_name):
        subprocess.run(
            [
                "ogr2ogr",
                "-f",
                "PostgreSQL",
                f"PG:host={self.params.get('DB_HOST')} user={self.params.get('DB_USER')} dbname={self.params.get('DB_NAME')} password={self.params.get('DB_PW')} port={self.params.get('DB_PORT')}",
                path,
                "-nlt", "PROMOTE_TO_MULTI",
                "-nln", table_name
            ]
        )

