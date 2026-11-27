#!/usr/bin/env python3
"""SmartSchool API - dependency-free SQLite backend for local academic demos."""
import json, os, sqlite3, hashlib, hmac, secrets, uuid
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('SMARTSCHOOL_DB', os.path.join(BASE, 'data', 'smartschool.db'))
HOST = os.environ.get('SMARTSCHOOL_HOST', '127.0.0.1')
PORT = int(os.environ.get('SMARTSCHOOL_PORT', '8000'))
TOKENS = {}
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 240000).hex()
    return salt, digest

def init_db():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_salt TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','librarian','student')), active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, student_code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, email TEXT UNIQUE, phone TEXT, class_name TEXT, section TEXT, roll_number TEXT, active INTEGER NOT NULL DEFAULT 1, registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, user_id INTEGER UNIQUE REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS librarians(id INTEGER PRIMARY KEY, employee_code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, email TEXT UNIQUE, active INTEGER NOT NULL DEFAULT 1, user_id INTEGER UNIQUE REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY, isbn TEXT UNIQUE, title TEXT NOT NULL, author TEXT NOT NULL, publisher TEXT, publication_year INTEGER, category_id INTEGER REFERENCES categories(id), description TEXT, language TEXT DEFAULT 'English', edition TEXT, shelf_number TEXT, total_quantity INTEGER NOT NULL CHECK(total_quantity>=0), available_quantity INTEGER NOT NULL CHECK(available_quantity>=0 AND available_quantity<=total_quantity), cover_url TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS book_transactions(id INTEGER PRIMARY KEY, transaction_code TEXT UNIQUE NOT NULL, student_id INTEGER NOT NULL REFERENCES students(id), book_id INTEGER NOT NULL REFERENCES books(id), issue_date TEXT NOT NULL, due_date TEXT NOT NULL, return_date TEXT, status TEXT NOT NULL CHECK(status IN ('Issued','Returned','Lost','Damaged')), fine_amount REAL NOT NULL DEFAULT 0, processed_by INTEGER REFERENCES librarians(id), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS reservations(id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id), book_id INTEGER NOT NULL REFERENCES books(id), status TEXT NOT NULL DEFAULT 'Pending', requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TEXT, UNIQUE(student_id,book_id,status));
        CREATE TABLE IF NOT EXISTS fines(id INTEGER PRIMARY KEY, transaction_id INTEGER NOT NULL REFERENCES book_transactions(id), student_id INTEGER NOT NULL REFERENCES students(id), amount REAL NOT NULL CHECK(amount>=0), paid_amount REAL NOT NULL DEFAULT 0 CHECK(paid_amount>=0), status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS fine_payments(id INTEGER PRIMARY KEY, fine_id INTEGER NOT NULL REFERENCES fines(id), amount REAL NOT NULL CHECK(amount>0), payment_method TEXT, reference TEXT, paid_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), student_id INTEGER REFERENCES students(id), title TEXT NOT NULL, message TEXT NOT NULL, is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS activity_logs(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), action TEXT NOT NULL, entity TEXT, entity_id INTEGER, details TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS system_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_books_title ON books(title); CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
        CREATE INDEX IF NOT EXISTS idx_txn_student ON book_transactions(student_id); CREATE INDEX IF NOT EXISTS idx_txn_due ON book_transactions(due_date,status);
        CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status); CREATE INDEX IF NOT EXISTS idx_notifications_student ON notifications(student_id,is_read);
        ''')
        salt, digest = hash_password('Admin@123')
        c.execute("INSERT OR IGNORE INTO users(username,password_salt,password_hash,role) VALUES(?,?,?,'admin')", ('admin',salt,digest))
        defaults = {'fine_per_day':'5','max_fine':'500','grace_days':'0','loan_days':'14','borrow_limit':'3'}
        for k,v in defaults.items(): c.execute('INSERT OR IGNORE INTO system_settings(key,value) VALUES(?,?)',(k,v))
        if c.execute('SELECT COUNT(*) FROM categories').fetchone()[0] == 0:
            c.executemany('INSERT INTO categories(name) VALUES(?)',[(x,) for x in ['Fiction','Science','Classic','Biography','Self Growth','History','Technology','Other']])

def rowdict(row): return dict(row) if row else None

def log(c, user, action, entity=None, entity_id=None, details=None):
    c.execute('INSERT INTO activity_logs(user_id,action,entity,entity_id,details) VALUES(?,?,?,?,?)',(user,action,entity,entity_id,json.dumps(details or {})))

class Handler(BaseHTTPRequestHandler):
    server_version = 'SmartSchoolAPI/1.0'
    def send_json(self, status, payload):
        raw=json.dumps(payload,ensure_ascii=False,default=str).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Access-Control-Allow-Origin','http://localhost:5173'); self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization'); self.send_header('Access-Control-Allow-Methods','GET, POST, PUT, DELETE, OPTIONS'); self.end_headers(); self.wfile.write(raw)
    def do_OPTIONS(self): self.send_json(200,{'ok':True})
    def body(self):
        n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or b'{}')
    def auth(self, roles=None):
        token=self.headers.get('Authorization','').replace('Bearer ',''); user=TOKENS.get(token)
        if not user: self.send_json(401,{'error':'Authentication required'}); return None
        if roles and user['role'] not in roles: self.send_json(403,{'error':'Insufficient permissions'}); return None
        return user
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/health': return self.send_json(200,{'ok':True,'service':'SmartSchool API','database':'SQLite'})
        user=self.auth(['admin','librarian','student'])
        if not user:return
        with connect() as c:
            if path=='/api/me': return self.send_json(200,user)
            if path=='/api/books':
                rows=c.execute('SELECT b.*,cat.name category FROM books b LEFT JOIN categories cat ON cat.id=b.category_id ORDER BY b.title').fetchall(); return self.send_json(200,[rowdict(x) for x in rows])
            if path=='/api/categories': return self.send_json(200,[rowdict(x) for x in c.execute('SELECT * FROM categories ORDER BY name')])
            if path=='/api/students':
                if user['role']=='student': return self.send_json(403,{'error':'Not permitted'})
                return self.send_json(200,[rowdict(x) for x in c.execute('SELECT * FROM students ORDER BY name')])
            if path=='/api/librarians':
                if user['role']!='admin': return self.send_json(403,{'error':'Admin only'})
                return self.send_json(200,[rowdict(x) for x in c.execute('SELECT id,employee_code,name,email,active FROM librarians ORDER BY name')])
            if path=='/api/transactions':
                q='SELECT t.*,b.title book_title,s.name student_name FROM book_transactions t JOIN books b ON b.id=t.book_id JOIN students s ON s.id=t.student_id'; args=()
                if user['role']=='student': q+=' WHERE t.student_id=(SELECT id FROM students WHERE user_id=?)'; args=(user['id'],)
                return self.send_json(200,[rowdict(x) for x in c.execute(q+' ORDER BY t.id DESC',args)])
            if path=='/api/reservations':
                q='SELECT r.*,b.title book_title,s.name student_name FROM reservations r JOIN books b ON b.id=r.book_id JOIN students s ON s.id=r.student_id'; args=()
                if user['role']=='student': q+=' WHERE r.student_id=(SELECT id FROM students WHERE user_id=?)'; args=(user['id'],)
                return self.send_json(200,[rowdict(x) for x in c.execute(q+' ORDER BY r.id DESC',args)])
            if path=='/api/fines':
                q='SELECT f.*,s.name student_name,t.transaction_code FROM fines f JOIN students s ON s.id=f.student_id JOIN book_transactions t ON t.id=f.transaction_id'; args=()
                if user['role']=='student': q+=' WHERE f.student_id=(SELECT id FROM students WHERE user_id=?)'; args=(user['id'],)
                return self.send_json(200,[rowdict(x) for x in c.execute(q+' ORDER BY f.id DESC',args)])
            if path=='/api/notifications':
                q='SELECT * FROM notifications'; args=()
                if user['role']=='student': q+=' WHERE student_id=(SELECT id FROM students WHERE user_id=?)'; args=(user['id'],)
                return self.send_json(200,[rowdict(x) for x in c.execute(q+' ORDER BY id DESC',args)])
            if path=='/api/settings':
                if user['role']!='admin': return self.send_json(403,{'error':'Admin only'})
                return self.send_json(200,{x['key']:x['value'] for x in c.execute('SELECT * FROM system_settings')})
            if path=='/api/dashboard':
                if user['role']=='student': return self.send_json(403,{'error':'Admin/librarian only'})
                data={
                  'total_books':c.execute('SELECT COALESCE(SUM(total_quantity),0) FROM books').fetchone()[0],
                  'available_books':c.execute('SELECT COALESCE(SUM(available_quantity),0) FROM books').fetchone()[0],
                  'issued_books':c.execute("SELECT COUNT(*) FROM book_transactions WHERE status='Issued'").fetchone()[0],
                  'students':c.execute('SELECT COUNT(*) FROM students WHERE active=1').fetchone()[0],
                  'overdue_books':c.execute("SELECT COUNT(*) FROM book_transactions WHERE status='Issued' AND due_date<?",(date.today().isoformat(),)).fetchone()[0],
                  'librarians':c.execute('SELECT COUNT(*) FROM librarians WHERE active=1').fetchone()[0],
                  'pending_reservations':c.execute("SELECT COUNT(*) FROM reservations WHERE status='Pending'").fetchone()[0],
                  'outstanding_fines':c.execute("SELECT COALESCE(SUM(amount-paid_amount),0) FROM fines WHERE status!='Paid'").fetchone()[0]}
                return self.send_json(200,data)
            if path=='/api/activity':
                if user['role']!='admin': return self.send_json(403,{'error':'Admin only'})
                return self.send_json(200,[rowdict(x) for x in c.execute('SELECT * FROM activity_logs ORDER BY id DESC LIMIT 100')])
        self.send_json(404,{'error':'Route not found'})
    def do_POST(self):
        path=urlparse(self.path).path; data=self.body()
        if path=='/api/login':
            with connect() as c:
                u=c.execute('SELECT * FROM users WHERE username=? AND active=1',(str(data.get('username','')),)).fetchone()
                if not u: return self.send_json(401,{'error':'Invalid username or password'})
                _,digest=hash_password(str(data.get('password','')),u['password_salt'])
                if not hmac.compare_digest(digest,u['password_hash']): return self.send_json(401,{'error':'Invalid username or password'})
                token=secrets.token_urlsafe(32); profile={'id':u['id'],'username':u['username'],'role':u['role']}; TOKENS[token]=profile
                log(c,u['id'],'login','user',u['id'])
                return self.send_json(200,{'token':token,'user':profile})
        allowed=['admin','librarian','student'] if path=='/api/reservations' else ['admin','librarian']
        user=self.auth(allowed)
        if not user:return
        with connect() as c:
            if path=='/api/librarians':
                if user['role']!='admin':return self.send_json(403,{'error':'Admin only'})
                try:
                    salt,digest=hash_password(data['password']); cur=c.execute("INSERT INTO users(username,password_salt,password_hash,role) VALUES(?,?,?,'librarian')",(data['username'],salt,digest))
                    lid=c.execute('INSERT INTO librarians(employee_code,name,email,user_id) VALUES(?,?,?,?)',(data['employee_code'],data['name'],data.get('email'),cur.lastrowid)).lastrowid
                    log(c,user['id'],'librarian_created','librarian',lid); return self.send_json(201,{'id':lid})
                except (KeyError,sqlite3.IntegrityError):return self.send_json(400,{'error':'Required fields missing or username/employee code already exists'})
            if path=='/api/books':
                title=str(data.get('title','')).strip(); author=str(data.get('author','')).strip(); qty=int(data.get('total_quantity',1))
                if not title or not author or qty<0:return self.send_json(400,{'error':'Title, author and a non-negative quantity are required'})
                cat=data.get('category_id')
                cur=c.execute('INSERT INTO books(isbn,title,author,publisher,publication_year,category_id,description,language,edition,shelf_number,total_quantity,available_quantity,cover_url) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(data.get('isbn') or None,title,author,data.get('publisher'),data.get('publication_year'),cat,data.get('description'),data.get('language','English'),data.get('edition'),data.get('shelf_number'),qty,qty,data.get('cover_url')))
                log(c,user['id'],'book_created','book',cur.lastrowid); return self.send_json(201,{'id':cur.lastrowid})
            if path=='/api/students':
                if user['role']!='admin':return self.send_json(403,{'error':'Admin only'})
                try:
                    cur=c.execute('INSERT INTO students(student_code,name,email,phone,class_name,section,roll_number) VALUES(?,?,?,?,?,?,?)',(data['student_code'],data['name'],data.get('email'),data.get('phone'),data.get('class_name'),data.get('section'),data.get('roll_number')))
                    log(c,user['id'],'student_created','student',cur.lastrowid); return self.send_json(201,{'id':cur.lastrowid})
                except (KeyError,sqlite3.IntegrityError) as e:return self.send_json(400,{'error':'Required student fields missing or duplicate student code/email'})
            if path=='/api/transactions/issue':
                try:
                    sid=int(data['student_id']); bid=int(data['book_id']); due=data['due_date']
                    book=c.execute('SELECT * FROM books WHERE id=?',(bid,)).fetchone(); student=c.execute('SELECT * FROM students WHERE id=? AND active=1',(sid,)).fetchone()
                    if not book or book['available_quantity']<1:return self.send_json(409,{'error':'Book unavailable'})
                    if not student:return self.send_json(404,{'error':'Active student not found'})
                    limit=int(c.execute("SELECT value FROM system_settings WHERE key='borrow_limit'").fetchone()[0])
                    active=c.execute("SELECT COUNT(*) FROM book_transactions WHERE student_id=? AND status='Issued'",(sid,)).fetchone()[0]
                    if active>=limit:return self.send_json(409,{'error':'Student borrowing limit reached'})
                    code='TX-'+uuid.uuid4().hex[:10].upper(); cur=c.execute("INSERT INTO book_transactions(transaction_code,student_id,book_id,issue_date,due_date,status,processed_by) VALUES(?,?,?,?,?,'Issued',?)",(code,sid,bid,date.today().isoformat(),due,data.get('processed_by')))
                    c.execute('UPDATE books SET available_quantity=available_quantity-1 WHERE id=? AND available_quantity>0',(bid,))
                    c.execute('INSERT INTO notifications(student_id,title,message) VALUES(?,?,?)',(sid,'Book issued',f'{book["title"]} is due on {due}.'))
                    log(c,user['id'],'book_issued','transaction',cur.lastrowid,{'code':code}); return self.send_json(201,{'id':cur.lastrowid,'transaction_code':code})
                except (KeyError,ValueError):return self.send_json(400,{'error':'student_id, book_id and due_date are required'})
            if path=='/api/transactions/return':
                try:
                    tid=int(data['transaction_id']); t=c.execute("SELECT * FROM book_transactions WHERE id=? AND status='Issued'",(tid,)).fetchone()
                    if not t:return self.send_json(404,{'error':'Active transaction not found or already returned'})
                    returned=date.today(); late=max(0,(returned-date.fromisoformat(t['due_date'])).days)
                    settings={x['key']:x['value'] for x in c.execute('SELECT * FROM system_settings')}; grace=int(settings.get('grace_days','0')); rate=float(settings.get('fine_per_day','5')); cap=float(settings.get('max_fine','500'))
                    fine=min(cap,max(0,late-grace)*rate); c.execute("UPDATE book_transactions SET status='Returned',return_date=?,fine_amount=? WHERE id=? AND status='Issued'",(returned.isoformat(),fine,tid))
                    c.execute('UPDATE books SET available_quantity=available_quantity+1 WHERE id=? AND available_quantity<total_quantity',(t['book_id'],))
                    if fine>0:c.execute('INSERT INTO fines(transaction_id,student_id,amount) VALUES(?,?,?)',(tid,t['student_id'],fine))
                    c.execute('INSERT INTO notifications(student_id,title,message) VALUES(?,?,?)',(t['student_id'],'Book returned',f'Return processed. Fine: ₹{fine:.2f}'))
                    log(c,user['id'],'book_returned','transaction',tid,{'fine':fine}); return self.send_json(200,{'ok':True,'fine':fine,'late_days':late})
                except (KeyError,ValueError):return self.send_json(400,{'error':'transaction_id is required'})
            if path=='/api/fine-payments':
                try:
                    fid=int(data['fine_id']); amount=float(data['amount']); f=c.execute('SELECT * FROM fines WHERE id=?',(fid,)).fetchone()
                    if not f or amount<=0 or amount>f['amount']-f['paid_amount']:return self.send_json(400,{'error':'Invalid payment amount or fine'})
                    c.execute('INSERT INTO fine_payments(fine_id,amount,payment_method,reference) VALUES(?,?,?,?)',(fid,amount,data.get('payment_method','Cash'),data.get('reference')))
                    paid=f['paid_amount']+amount; c.execute('UPDATE fines SET paid_amount=?,status=? WHERE id=?',(paid,'Paid' if paid>=f['amount'] else 'Partially Paid',fid)); log(c,user['id'],'fine_payment_recorded','fine',fid,{'amount':amount}); return self.send_json(201,{'ok':True,'paid_amount':paid})
                except (KeyError,ValueError):return self.send_json(400,{'error':'fine_id and amount are required'})
            if path=='/api/reservations':
                try:
                    sid=int(data['student_id']) if user['role']!='student' else c.execute('SELECT id FROM students WHERE user_id=?',(user['id'],)).fetchone()['id']
                    cur=c.execute("INSERT INTO reservations(student_id,book_id,status) VALUES(?,?,'Pending')",(sid,int(data['book_id'])))
                    log(c,user['id'],'reservation_created','reservation',cur.lastrowid); return self.send_json(201,{'id':cur.lastrowid})
                except (KeyError,sqlite3.IntegrityError,ValueError):return self.send_json(400,{'error':'Invalid or duplicate active reservation'})
        self.send_json(404,{'error':'Route not found'})
    def do_PUT(self):
        path=urlparse(self.path).path; data=self.body(); user=self.auth(['admin','librarian'])
        if not user:return
        with connect() as c:
            if path.startswith('/api/books/'):
                bid=path.rsplit('/',1)[-1]; b=c.execute('SELECT * FROM books WHERE id=?',(bid,)).fetchone()
                if not b:return self.send_json(404,{'error':'Book not found'})
                qty=int(data.get('total_quantity',b['total_quantity'])); issued=b['total_quantity']-b['available_quantity']
                if qty<issued:return self.send_json(409,{'error':'Quantity cannot be lower than currently issued copies'})
                c.execute('UPDATE books SET title=?,author=?,isbn=?,total_quantity=?,available_quantity=? WHERE id=?',(data.get('title',b['title']),data.get('author',b['author']),data.get('isbn',b['isbn']),qty,qty-issued,bid)); log(c,user['id'],'book_updated','book',int(bid)); return self.send_json(200,{'ok':True})
            if path.startswith('/api/reservations/'):
                rid=path.rsplit('/',1)[-1]; status=data.get('status')
                if status not in ['Approved','Rejected','Available for Pickup','Completed','Expired','Cancelled']:return self.send_json(400,{'error':'Invalid reservation status'})
                cur=c.execute('UPDATE reservations SET status=? WHERE id=?',(status,rid))
                if cur.rowcount==0:return self.send_json(404,{'error':'Reservation not found'})
                r=c.execute('SELECT student_id FROM reservations WHERE id=?',(rid,)).fetchone(); c.execute('INSERT INTO notifications(student_id,title,message) VALUES(?,?,?)',(r['student_id'],'Reservation update',f'Your reservation status is now {status}.')); return self.send_json(200,{'ok':True})
            if path.startswith('/api/notifications/'):
                nid=path.rsplit('/',1)[-1]; c.execute('UPDATE notifications SET is_read=1 WHERE id=?',(nid,)); return self.send_json(200,{'ok':True})
            if path=='/api/settings':
                if user['role']!='admin':return self.send_json(403,{'error':'Admin only'})
                for k,v in data.items():c.execute('INSERT INTO system_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,str(v)))
                return self.send_json(200,{'ok':True})
        self.send_json(404,{'error':'Route not found'})
    def do_DELETE(self):
        path=urlparse(self.path).path; user=self.auth(['admin'])
        if not user:return
        with connect() as c:
            if path.startswith('/api/books/'):
                bid=path.rsplit('/',1)[-1]
                if c.execute("SELECT COUNT(*) FROM book_transactions WHERE book_id=? AND status='Issued'",(bid,)).fetchone()[0]:return self.send_json(409,{'error':'Cannot delete a book with active issue records'})
                cur=c.execute('DELETE FROM books WHERE id=?',(bid,)); return self.send_json(200 if cur.rowcount else 404,{'ok':bool(cur.rowcount)})
            if path.startswith('/api/students/'):
                sid=path.rsplit('/',1)[-1]
                if c.execute("SELECT COUNT(*) FROM book_transactions WHERE student_id=? AND status='Issued'",(sid,)).fetchone()[0]:return self.send_json(409,{'error':'Student has active borrowed books'})
                cur=c.execute('UPDATE students SET active=0 WHERE id=?',(sid,)); return self.send_json(200 if cur.rowcount else 404,{'ok':bool(cur.rowcount)})
        self.send_json(404,{'error':'Route not found'})
    def log_message(self, fmt, *args): print('%s - %s' % (self.address_string(),fmt%args))

if __name__=='__main__':
    init_db(); print(f'SmartSchool API running at http://{HOST}:{PORT}'); print('Demo admin login: admin / Admin@123 (change before real use)')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
