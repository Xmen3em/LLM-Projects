import psycopg2  
from psycopg2 import Error  

class DBConnector:  
    def __init__(self):  
        self.connection = psycopg2.connect(  
            user="postgres",  
            password="abdo@@@@2022",  
            host="localhost",  
            port="5432",  
            database="car_task_database"  
        )  
        self.cursor = self.connection.cursor()  

    def execute_query(self, query, params=None):  
        try:  
            self.cursor.execute(query, params)  
            self.connection.commit()  
            return self.cursor.fetchall()  
        except Error as e:  
            print(f"Database error: {e}")  
            self.connection.rollback()  

    def close(self):  
        self.cursor.close()  
        self.connection.close()  