This text includes commend how to run the Article Submission System.
open the mysql script in mysql workbench and run the script.it will create a whole empty data base with the needed tables in it.

enter the app.py and change user and password name to your mysql username and password it shoul look like This

def create_connection():
    """Create a database connection"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='your mysql username',
            password='your mysql password',
            database='MYArticleHub'
        )
        if connection.is_connected():
            return connection
    except Error as e:
        logging.error(f"Error: '{e}'")
    return None

after you entered your information run the app.py.it will run at the background while you surfe in the app
oper the index.html file as you like(recommend to just click to the file and open in google chrome)
now you can surfe in the app.

First signin with proper format.
then login with your username and password.
in the main page you can upload articles with your username
you can see the articles you uploaded at main page.if you click read more you can see the whole article and send a feedback note with a score.

if you set up the mysql correctly. open the make admin script in mysql folder and enter your username to usrername field it should look like This

USE MYArticleHub;

UPDATE Users
SET role = 'admin'
WHERE username = 'your_app_username';

and run the script, now your user is an admin.in the main page you can enter the panel with your username and password and acces to admin panel.
if you have any question connect us from omer395@ogr.eskisehir.edu.tr  or  gizemtuguz@ogr.eskisehir.edu.tr
