import mysql.connector
from mysql.connector import Error
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
from email.parser import BytesParser
from email.policy import default
from urllib.parse import urlparse, parse_qs


logging.basicConfig(level=logging.DEBUG)

def create_connection():
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='poyrazzo',
            database='MYArticleHub'
        )
        if connection.is_connected():
            return connection
    except Error as e:
        logging.error(f"Error: '{e}'")
    return None

def fetch_articles(connection):
    
    query = "SELECT article_id, title, content FROM Articles"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)
    articles = cursor.fetchall()
    cursor.close()
    return articles

def fetch_article_by_id(connection, article_id):
    
    query = """
    SELECT title, content, username
    FROM Articles
    WHERE article_id = %s
    """
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (article_id,))
    article = cursor.fetchone()
    cursor.close()
    return article

def fetch_feedback_notes(connection, article_id):
    
    query = """
    SELECT feedback_note
    FROM Feedback
    WHERE article_id = %s
    """
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (article_id,))
    feedback_notes = cursor.fetchall()
    cursor.close()
    return feedback_notes

def fetch_top_articles(connection):
    
    query = """
    SELECT article_id, title, feedback_score
    FROM Articles
    ORDER BY feedback_score DESC
    LIMIT 10
    """
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)
    top_articles = cursor.fetchall()
    cursor.close()

    
    for article in top_articles:
        article['feedback_score'] = float(article['feedback_score'])

    return top_articles

def search_articles(connection, search_query):
    
    query = """
    SELECT article_id, title, content
    FROM Articles
    WHERE title LIKE %s
    """
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, ('%' + search_query + '%',))
    articles = cursor.fetchall()
    cursor.close()
    return articles

def save_feedback(connection, article_id, score, feedback_note):
    
    try:
        cursor = connection.cursor()
       
        feedback_query = "INSERT INTO Feedback (article_id, score, feedback_note) VALUES (%s, %s, %s)"
        cursor.execute(feedback_query, (article_id, score, feedback_note))

       
        recalculate_feedback_score(connection, article_id)

        connection.commit()
        cursor.close()
        return True
    except Error as e:
        logging.error(f"Error: '{e}'")
        return False

def recalculate_feedback_score(connection, article_id):
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT SUM(score) as total_score, COUNT(*) as total_count FROM Feedback WHERE article_id = %s"
        cursor.execute(query, (article_id,))
        result = cursor.fetchone()
        if result and result['total_count'] > 0:
            average_score = result['total_score'] / result['total_count']
        else:
            average_score = 0

        
        update_query = "UPDATE Articles SET feedback_score = %s, feedback_count = %s WHERE article_id = %s"
        cursor.execute(update_query, (average_score, result['total_count'], article_id))
        cursor.close()
    except Error as e:
        logging.error(f"Error: '{e}'")

def save_report(connection, article_id, report_note):
    
    try:
        cursor = connection.cursor()
        report_query = "INSERT INTO Reports (article_id, report_note) VALUES (%s, %s)"
        cursor.execute(report_query, (article_id, report_note))
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        logging.error(f"Error: '{e}'")
        return False

def get_user_role(connection, username, password):
    
    query = "SELECT role FROM Users WHERE username = %s AND password = %s"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    cursor.close()
    return user

def fetch_users(connection):
    
    query = "SELECT user_id, username, email, full_name, role FROM Users"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)
    users = cursor.fetchall()
    cursor.close()
    return users

def update_user_role(connection, user_id, new_role):
    
    query = "UPDATE Users SET role = %s WHERE user_id = %s"
    cursor = connection.cursor()
    try:
        cursor.execute(query, (new_role, user_id))
        connection.commit()
    except Error as e:
        logging.error(f"Error executing query: {e}")
    cursor.close()

def remove_user(connection, user_id):
    
    query = "DELETE FROM Users WHERE user_id = %s"
    cursor = connection.cursor()
    try:
        cursor.execute(query, (user_id,))
        connection.commit()
    except Error as e:
        logging.error(f"Error executing query: {e}")
    cursor.close()

def save_article(connection, article):
    
    query = """
    INSERT INTO Articles (username, title, content)
    VALUES (%s, %s, %s)
    """
    cursor = connection.cursor()
    try:
        cursor.execute(query, article)
        connection.commit()
        logging.info("Article saved successfully")
    except Error as e:
        logging.error(f"Error executing query: {e}")
    finally:
        cursor.close()

def username_exists(connection, username):
    
    query = "SELECT 1 FROM Users WHERE username = %s"
    cursor = connection.cursor()
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None

def verify_user(connection, username, password):
    
    query = "SELECT password FROM Users WHERE username = %s"
    cursor = connection.cursor()
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    cursor.close()
    if result:
        stored_password = result[0]
        return stored_password == password
    return None

def save_user(connection, user):
    
    query = """
    INSERT INTO Users (username, password, email, full_name)
    VALUES (%s, %s, %s, %s)
    """
    cursor = connection.cursor()
    try:
        cursor.execute(query, user)
        connection.commit()
        logging.info("User saved successfully")
    except Error as e:
        logging.error(f"Error executing query: {e}")
    finally:
        cursor.close()

class RequestHandler(BaseHTTPRequestHandler):
    def parse_multipart(self, data):
        
        parser = BytesParser(policy=default)
        headers = {
            'Content-Type': self.headers['Content-Type']
        }
        msg = parser.parsebytes(b'\r\n'.join([f"{k}: {v}".encode('utf-8') for k, v in headers.items()]) + b'\r\n\r\n' + data)
        form_data = {}
        for part in msg.iter_parts():
            if part.get_content_disposition() == 'form-data':
                name = part.get_param('name', header='content-disposition')
                form_data[name] = part.get_payload(decode=True).decode('utf-8')
        return form_data

    def do_OPTIONS(self):
        
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/articles'):
            connection = create_connection()
            if connection:
                articles = fetch_articles(connection)
                connection.close()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(articles).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Failed to connect to the database")

        elif self.path.startswith('/article'):
            query_components = parse_qs(urlparse(self.path).query)
            article_id = query_components.get('id', [None])[0]

            if article_id:
                connection = create_connection()
                if connection:
                    article = fetch_article_by_id(connection, article_id)
                    connection.close()

                    if article:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(article).encode('utf-8'))
                    else:
                        self.send_response(404)
                        self.send_header('Content-type', 'text/html')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b"Article not found")
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Failed to connect to the database")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Invalid article ID")

        elif self.path.startswith('/feedbacks'):
            query_components = parse_qs(urlparse(self.path).query)
            article_id = query_components.get('article_id', [None])[0]

            if article_id:
                connection = create_connection()
                if connection:
                    feedback_notes = fetch_feedback_notes(connection, article_id)
                    connection.close()

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(feedback_notes).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Failed to connect to the database")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Invalid article ID")

        elif self.path.startswith('/top_articles'):
            connection = create_connection()
            if connection:
                top_articles = fetch_top_articles(connection)
                connection.close()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(top_articles).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Failed to connect to the database")

        elif self.path.startswith('/search_articles'):
            query_components = parse_qs(urlparse(self.path).query)
            search_query = query_components.get('query', [None])[0]

            if search_query:
                connection = create_connection()
                if connection:
                    articles = search_articles(connection, search_query)
                    connection.close()

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(articles).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Failed to connect to the database")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Invalid search query")

        elif self.path.startswith('/users'):
            connection = create_connection()
            if connection:
                users = fetch_users(connection)
                connection.close()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(users).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Failed to connect to the database")

    def do_POST(self):
        if self.path == '/feedback':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            feedback_data = json.loads(post_data)

            article_id = feedback_data.get('articleId')
            score = feedback_data.get('score')
            feedback_note = feedback_data.get('feedbackNote')

            if article_id and score is not None and feedback_note:
                connection = create_connection()
                if connection:
                    success = save_feedback(connection, article_id, score, feedback_note)
                    connection.close()

                    if success:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'message': 'Feedback submitted successfully'}).encode('utf-8'))
                    else:
                        self.send_response(500)
                        self.send_header('Content-type', 'text/html')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b"Failed to submit feedback")
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Failed to connect to the database")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Invalid feedback data")

        elif self.path == '/report':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            report_data = json.loads(post_data)

            article_id = report_data.get('articleId')
            report_note = report_data.get('reportNote')

            if article_id and report_note:
                connection = create_connection()
                if connection:
                    success = save_report(connection, article_id, report_note)
                    connection.close()

                    if success:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'message': 'Report submitted successfully'}).encode('utf-8'))
                    else:
                        self.send_response(500)
                        self.send_header('Content-type', 'text/html')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b"Failed to submit report")
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Failed to connect to the database")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Invalid report data")

        elif self.path == '/admin_login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            login_data = json.loads(post_data)

            username = login_data.get('username')
            password = login_data.get('password')

            if username and password:
                connection = create_connection()
                if connection:
                    user = get_user_role(connection, username, password)
                    connection.close()

                    if user and user['role'] == 'admin':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'role': 'admin'}).encode('utf-8'))
                    else:
                        self.send_response(403)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'role': 'user'}).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Failed to connect to the database")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Invalid login data")

        elif self.path == '/update_role':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data)

            user_id = update_data.get('user_id')
            new_role = update_data.get('new_role')

            if user_id and new_role:
                connection = create_connection()
                if connection:
                    update_user_role(connection, user_id, new_role)
                    connection.close()
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'message': 'User role updated successfully'}).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Failed to connect to the database")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'User ID and new role are required'}).encode('utf-8'))

        elif self.path == '/remove_user':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            remove_data = json.loads(post_data)

            user_id = remove_data.get('user_id')

            if user_id:
                connection = create_connection()
                if connection:
                    remove_user(connection, user_id)
                    connection.close()
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'message': 'User removed successfully'}).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Failed to connect to the database")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'User ID is required'}).encode('utf-8'))

        elif self.path == '/upload':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            logging.debug(f"Received raw post data: {post_data}")

            form_data = self.parse_multipart(post_data)
            logging.debug(f"Parsed form data: {form_data}")

            title = form_data.get('title')
            content = form_data.get('content')
            username = form_data.get('username')

            if not title or not content or not username:
                logging.error("One or more form fields are empty.")
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Form fields cannot be empty")
                return

            connection = create_connection()
            if connection:
                if not username_exists(connection, username):
                    logging.error("Username not found.")
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Username not found")
                    return
                
                article = (username, title, content)
                save_article(connection, article)
                connection.close()
                logging.info("Article saved successfully")
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Article uploaded successfully")
            else:
                logging.error("Failed to connect to the database")
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Failed to connect to the database")

        elif self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            logging.debug(f"Received raw post data: {post_data}")
            
            form_data = self.parse_multipart(post_data)
            logging.debug(f"Parsed form data: {form_data}")

            username = form_data.get('username')
            password = form_data.get('password')

            if not username or not password:
                logging.error("Username or password field is empty.")
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Username or password cannot be empty")
                return

            connection = create_connection()
            if connection:
                user_verified = verify_user(connection, username, password)
                if user_verified is None:
                    logging.error("Username does not exist.")
                    self.send_response(404)  
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Username does not exist")
                elif not user_verified:
                    logging.error("Password incorrect.")
                    self.send_response(401)  
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Password incorrect")
                else:
                    logging.info("User logged in successfully")
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Login successful")
            else:
                logging.error("Failed to connect to the database")
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Failed to connect to the database")

        elif self.path == '/signup':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            logging.debug(f"Received raw post data: {post_data}")
            
            form_data = self.parse_multipart(post_data)
            logging.debug(f"Parsed form data: {form_data}")

            full_name = form_data.get('full_name')
            username = form_data.get('username')
            email = form_data.get('email')
            password = form_data.get('password')

            if not full_name or not username or not email or not password:
                logging.error("One or more form fields are empty.")
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Form fields cannot be empty")
                return

            connection = create_connection()
            if connection:
                if username_exists(connection, username):
                    logging.error("Username already exists.")
                    self.send_response(409)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Username already exists")
                else:
                    user = (username, password, email, full_name)
                    save_user(connection, user)
                    connection.close()
                    logging.info("User saved successfully")
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"User created successfully")
            else:
                logging.error("Failed to connect to the database")
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Failed to connect to the database")

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f'Starting httpd server on port {port}...')
    httpd.serve_forever()

if __name__ == "__main__":
    run()
