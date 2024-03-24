import mysql.connector

dataBase = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    password = 'root'
)

#Prepare a cursor object
cursorObject = dataBase.cursor()

#Create a database

cursorObject.execute("CREATE DATABASE DLDataBase")

print("All done")
