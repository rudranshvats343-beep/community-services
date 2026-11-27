import { useMemo, useState } from 'react';
import {
  LayoutDashboard, BookOpen, Users, ArrowLeftRight, RotateCcw,
  ChartNoAxesCombined, Settings, Search, Bell, Plus, MoreHorizontal,
  BookMarked, Clock3, CircleCheck, AlertTriangle, Menu, X, Sparkles,
  LibraryBig, ChevronRight, Trash2, Pencil, CalendarDays, GraduationCap
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, CartesianGrid, XAxis, YAxis,
  Tooltip, BarChart, Bar
} from 'recharts';

const seedBooks = [
  {id:1,title:'The Silent Patient',author:'Alex Michaelides',category:'Fiction',isbn:'9781250301697',copies:4,available:3,color:'plum'},
  {id:2,title:'Atomic Habits',author:'James Clear',category:'Self Growth',isbn:'9780735211292',copies:6,available:4,color:'sage'},
  {id:3,title:'The Great Gatsby',author:'F. Scott Fitzgerald',category:'Classic',isbn:'9780743273565',copies:3,available:2,color:'navy'},
  {id:4,title:'A Brief History of Time',author:'Stephen Hawking',category:'Science',isbn:'9780553380163',copies:5,available:5,color:'sand'},
  {id:5,title:'Wings of Fire',author:'A. P. J. Abdul Kalam',category:'Biography',isbn:'9788173711466',copies:8,available:6,color:'rust'},
  {id:6,title:'The Alchemist',author:'Paulo Coelho',category:'Fiction',isbn:'9780061122415',copies:4,available:2,color:'teal'}
];
const seedStudents = [
  {id:1,name:'Aarav Sharma',roll:'ST-1024',className:'10-A',email:'aarav@school.edu'},
  {id:2,name:'Ananya Verma',roll:'ST-1025',className:'9-B',email:'ananya@school.edu'},
  {id:3,name:'Ishaan Gupta',roll:'ST-1026',className:'10-B',email:'ishaan@school.edu'}
];
const seedIssues = [
  {id:1,bookId:2,studentId:1,issueDate:'2026-11-18',dueDate:'2026-11-25',returnDate:'',status:'Issued'},
  {id:2,bookId:5,studentId:2,issueDate:'2026-11-10',dueDate:'2026-11-17',returnDate:'',status:'Overdue'},
  {id:3,bookId:3,studentId:3,issueDate:'2026-11-20',dueDate:'2026-11-27',returnDate:'',status:'Issued'}
];
const read = (key, fallback) => {
  try { const value = localStorage.getItem(key); return value ? JSON.parse(value) : fallback; }
  catch { return fallback; }
};
const save = (key, value) => localStorage.setItem(key, JSON.stringify(value));
const today = () => new Date().toISOString().slice(0,10);

function App() {
  const [page,setPage] = useState('Overview');
  const [books,setBooks] = useState(()=>read('ss-books',seedBooks));
  const [students,setStudents] = useState(()=>read('ss-students',seedStudents));
  const [issues,setIssues] = useState(()=>read('ss-issues',seedIssues));
  const [query,setQuery] = useState('');
  const [showBook,setShowBook] = useState(false);
  const [showStudent,setShowStudent] = useState(false);
  const [showIssue,setShowIssue] = useState(false);
  const [editingBook,setEditingBook] = useState(null);
  const [bookForm,setBookForm] = useState({title:'',author:'',category:'Fiction',isbn:'',copies:1});
  const [studentForm,setStudentForm] = useState({name:'',roll:'',className:'',email:''});
  const [issueForm,setIssueForm] = useState({bookId:'',studentId:'',dueDate:''});
  const [mobileOpen,setMobileOpen] = useState(false);
  const [notice,setNotice] = useState('');

  const setData = (setter,key,value) => { setter(value); save(key,value); };
  const activeIssues = issues.filter(x=>x.status!=='Returned');
  const overdue = activeIssues.filter(x=>x.dueDate < today());
  const totalCopies = books.reduce((n,b)=>n+Number(b.copies),0);
  const availableCopies = books.reduce((n,b)=>n+Number(b.available),0);
  const filteredBooks = useMemo(()=>books.filter(b=>
    `${b.title} ${b.author} ${b.category} ${b.isbn}`.toLowerCase().includes(query.toLowerCase())
  ),[books,query]);
  const filteredStudents = students.filter(s=>
    `${s.name} ${s.roll} ${s.className}`.toLowerCase().includes(query.toLowerCase())
  );

  function flash(message) { setNotice(message); setTimeout(()=>setNotice(''),2600); }
  function openNewBook() { setEditingBook(null); setBookForm({title:'',author:'',category:'Fiction',isbn:'',copies:1}); setShowBook(true); }
  function submitBook(e) {
    e.preventDefault();
    const copies = Math.max(1,Number(bookForm.copies)||1);
    let next;
    if(editingBook) {
      next=books.map(b=>b.id===editingBook.id?{...b,...bookForm,copies,available:Math.min(b.available,copies)}:b);
    } else {
      next=[{...bookForm,id:Date.now(),copies,available:copies,color:['plum','sage','navy','sand','rust','teal'][books.length%6]},...books];
    }
    setData(setBooks,'ss-books',next); setShowBook(false); flash(editingBook?'Book updated':'Book added to catalogue');
  }
  function removeBook(id) {
    if(issues.some(i=>i.bookId===id && i.status!=='Returned')) { flash('Return this book before deleting it'); return; }
    if(confirm('Delete this book record?')) { setData(setBooks,'ss-books',books.filter(b=>b.id!==id)); flash('Book deleted'); }
  }
  function submitStudent(e) {
    e.preventDefault();
    if(students.some(s=>s.roll.toLowerCase()===studentForm.roll.toLowerCase())) { flash('This roll number already exists'); return; }
    setData(setStudents,'ss-students',[{...studentForm,id:Date.now()},...students]);
    setStudentForm({name:'',roll:'',className:'',email:''}); setShowStudent(false); flash('Student registered');
  }
  function submitIssue(e) {
    e.preventDefault();
    const bookId=Number(issueForm.bookId), studentId=Number(issueForm.studentId);
    const book=books.find(b=>b.id===bookId);
    if(!book || book.available<1) { flash('No copies available for this book'); return; }
    const nextBooks=books.map(b=>b.id===bookId?{...b,available:b.available-1}:b);
    const nextIssues=[{id:Date.now(),bookId,studentId,issueDate:today(),dueDate:issueForm.dueDate,status:'Issued',returnDate:''},...issues];
    setData(setBooks,'ss-books',nextBooks); setData(setIssues,'ss-issues',nextIssues);
    setShowIssue(false); setIssueForm({bookId:'',studentId:'',dueDate:''}); flash('Book issued successfully');
  }
  function returnBook(issue) {
    if(!confirm('Mark this book as returned?')) return;
    const nextIssues=issues.map(i=>i.id===issue.id?{...i,status:'Returned',returnDate:today()}:i);
    const nextBooks=books.map(b=>b.id===issue.bookId?{...b,available:b.available+1}:b);
    setData(setIssues,'ss-issues',nextIssues); setData(setBooks,'ss-books',nextBooks); flash('Book return recorded');
  }
  const bookName=id=>books.find(b=>b.id===id)?.title||'Removed book';
  const studentName=id=>students.find(s=>s.id===id)?.name||'Unknown student';

  const nav=[
    {group:'WORKSPACE',items:[['Overview',LayoutDashboard],['Book Catalogue',BookOpen],['Students',Users],['Issue & Return',ArrowLeftRight]]},
    {group:'INSIGHTS',items:[['Overdue Books',Clock3],['Reports',ChartNoAxesCombined]]}
  ];
  const changePage=p=>{setPage(p);setMobileOpen(false);setQuery('');};

  return <div className="app-shell">
    <aside className={`sidebar ${mobileOpen?'open':''}`}>
      <div className="brand"><div className="brand-mark"><LibraryBig size={21}/></div><div><b>SmartSchool</b><small>LIBRARY CLOUD</small></div><button className="mobile-close" onClick={()=>setMobileOpen(false)}><X size={18}/></button></div>
      <div className="workspace-label">WORKSPACE <ChevronRight size={13}/></div>
      {nav.map(group=><div className="nav-group" key={group.group}><p>{group.group}</p>{group.items.map(([name,Icon])=><button key={name} className={`nav-item ${page===name?'active':''}`} onClick={()=>changePage(name)}><Icon size={17}/><span>{name}</span>{name==='Overdue Books'&&overdue.length>0&&<i>{overdue.length}</i>}</button>)}</div>)}
      <div className="sidebar-bottom"><div className="help-card"><div className="help-icon"><Sparkles size={17}/></div><b>Library insights</b><p>Keep your collection organised and your readers inspired.</p><button onClick={()=>changePage('Reports')}>View reports <ChevronRight size={13}/></button></div><div className="profile"><div className="avatar">AD</div><div><b>Admin Desk</b><small>Administrator</small></div><MoreHorizontal size={18}/></div></div>
    </aside>
    {mobileOpen&&<button className="scrim" onClick={()=>setMobileOpen(false)} aria-label="Close menu"/>}
    <main className="main-area">
      <header className="topbar"><button className="mobile-menu" onClick={()=>setMobileOpen(true)}><Menu/></button><div className="crumb">Workspace <span>/</span> <b>{page}</b></div><div className="top-actions"><div className="system-pill"><span/> All systems operational</div><button className="icon-button" aria-label="Notifications" onClick={()=>flash('You are all caught up')}><Bell size={18}/><em/></button><div className="top-avatar">AD</div></div></header>
      <div className="page-content">
        <div className="page-heading"><div><div className="eyebrow"><Sparkles size={13}/> DIGITAL LIBRARY MANAGEMENT</div><h1>{page==='Overview'?'Your library, beautifully organised.':page}</h1><p>{page==='Overview'?'A clear view of your collection, readers and daily circulation.':page==='Book Catalogue'?'Manage titles, copies and availability across your collection.':page==='Students'?'Manage registered readers and their library access.':page==='Issue & Return'?'Track circulation and record book returns.':page==='Overdue Books'?'Follow up on books that have passed their due date.':'Understand how your library is being used.'}</p></div><div className="heading-date"><CalendarDays size={15}/>{new Date().toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})}</div></div>

        {page==='Overview'&&<>
          <section className="hero-panel"><div className="hero-copy"><div className="hero-tag"><span/> YOUR KNOWLEDGE SPACE</div><h2>A world of stories.<br/><i>One beautiful library.</i></h2><p>Every book has a place. Every reader has a story. Keep your school library moving forward.</p><button onClick={()=>changePage('Book Catalogue')}>Explore collection <ChevronRight size={16}/></button></div><div className="hero-art"><div className="orb orb-one"/><div className="orb orb-two"/><div className="shelf shelf-back"><div className="book-spine b1"/><div className="book-spine b2"/><div className="book-spine b3"/><div className="book-spine b4"/><div className="book-spine b5"/></div><div className="featured-book"><div className="book-cover"><span>THE ART OF</span><b>READING</b><small>A LIFE IN STORIES</small></div><div className="book-pages"/></div><div className="shelf shelf-front"><div className="book-spine b6"/><div className="book-spine b7"/><div className="book-spine b8"/><div className="book-spine b9"/></div><div className="floating-note"><BookOpen size={14}/><span><b>{books.length} titles</b><small>in your collection</small></span></div></div></section>
          <section className="stats-grid">
            <Stat icon={BookOpen} label="Total book copies" value={totalCopies} note={`${books.length} unique titles`} tone="blue"/>
            <Stat icon={BookMarked} label="Available copies" value={availableCopies} note="Ready to be borrowed" tone="green"/>
            <Stat icon={ArrowLeftRight} label="Currently issued" value={activeIssues.length} note="Active borrow records" tone="gold"/>
            <Stat icon={AlertTriangle} label="Overdue books" value={overdue.length} note="Need your attention" tone="rose"/>
          </section>
          <section className="content-grid"><div className="panel chart-panel"><div className="panel-head"><div><h3>Library activity</h3><p>Borrowing activity overview</p></div><span className="chart-period">Last 6 months</span></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={[{m:'Jun',v:18},{m:'Jul',v:25},{m:'Aug',v:21},{m:'Sep',v:37},{m:'Oct',v:31},{m:'Nov',v:48}]}><defs><linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#b99863" stopOpacity={.28}/><stop offset="100%" stopColor="#b99863" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e9e6df"/><XAxis dataKey="m" axisLine={false} tickLine={false} tick={{fill:'#8c8d91',fontSize:11}}/><YAxis axisLine={false} tickLine={false} tick={{fill:'#8c8d91',fontSize:11}}/><Tooltip/><Area type="monotone" dataKey="v" stroke="#b99863" strokeWidth={2.5} fill="url(#areaFill)"/></AreaChart></ResponsiveContainer></div></div><div className="panel collection-panel"><div className="panel-head"><div><h3>Collection snapshot</h3><p>Copy availability</p></div><BookMarked size={18} className="muted-icon"/></div><div className="collection-number">{availableCopies}<small> / {totalCopies} copies available</small></div><div className="progress"><span style={{width:`${totalCopies?availableCopies/totalCopies*100:0}%`}}/></div><div className="legend-row"><span><i className="dot available"/>Available</span><b>{totalCopies?Math.round(availableCopies/totalCopies*100):0}%</b></div><div className="legend-row"><span><i className="dot issued"/>Issued</span><b>{totalCopies?Math.round((totalCopies-availableCopies)/totalCopies*100):0}%</b></div><button className="text-link" onClick={()=>changePage('Book Catalogue')}>View inventory <ChevronRight size={14}/></button></div></section>
          <section className="panel recent-panel"><div className="panel-head"><div><h3>Recent circulation</h3><p>The latest book movements</p></div><button className="text-link" onClick={()=>changePage('Issue & Return')}>View all <ChevronRight size={14}/></button></div><IssueTable issues={issues.slice(0,4)} bookName={bookName} studentName={studentName} onReturn={returnBook}/></section>
        </>}

        {page==='Book Catalogue'&&<><div className="toolbar"><div className="search-box"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search title, author, category or ISBN..."/></div><button className="primary-button" onClick={openNewBook}><Plus size={17}/> Add a book</button></div><div className="book-grid">{filteredBooks.map(book=><div className="book-card" key={book.id}><div className={`book-visual ${book.color}`}><div className="visual-book"><small>{book.category.toUpperCase()}</small><b>{book.title}</b><span>{book.author}</span></div><span className="copy-chip">{book.available} available</span></div><div className="book-info"><div><h3>{book.title}</h3><p>{book.author}</p></div><div className="book-meta"><span>{book.isbn||'ISBN not added'}</span><b>{book.available}/{book.copies} copies</b></div><div className="book-actions"><button onClick={()=>{setEditingBook(book);setBookForm({...book});setShowBook(true)}}><Pencil size={14}/> Edit</button><button onClick={()=>removeBook(book.id)}><Trash2 size={14}/> Delete</button></div></div></div>)}</div>{filteredBooks.length===0&&<Empty text="No books match your search."/>}</>}

        {page==='Students'&&<><div className="toolbar"><div className="search-box"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search student, roll number or class..."/></div><button className="primary-button" onClick={()=>setShowStudent(true)}><Plus size={17}/> Add student</button></div><div className="panel table-panel"><div className="panel-head"><div><h3>Registered readers</h3><p>{students.length} students in your library</p></div><Users size={18} className="muted-icon"/></div><div className="table-scroll"><table><thead><tr><th>STUDENT</th><th>ROLL NUMBER</th><th>CLASS</th><th>EMAIL</th><th>BOOKS OUT</th></tr></thead><tbody>{filteredStudents.map(s=><tr key={s.id}><td><div className="person-cell"><div className="person-avatar">{s.name.split(' ').map(x=>x[0]).slice(0,2).join('')}</div><b>{s.name}</b></div></td><td>{s.roll}</td><td>{s.className}</td><td>{s.email||'—'}</td><td><span className="count-pill">{issues.filter(i=>i.studentId===s.id&&i.status!=='Returned').length}</span></td></tr>)}</tbody></table></div>{filteredStudents.length===0&&<Empty text="No students found."/ >}</div></>}

        {page==='Issue & Return'&&<><div className="toolbar"><div className="search-box"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search by book or student..."/></div><button className="primary-button" onClick={()=>{setIssueForm({bookId:'',studentId:'',dueDate:''});setShowIssue(true)}}><Plus size={17}/> Issue a book</button></div><div className="panel table-panel"><div className="panel-head"><div><h3>Circulation records</h3><p>All active and returned books</p></div><ArrowLeftRight size={18} className="muted-icon"/></div><IssueTable issues={issues.filter(i=>(bookName(i.bookId)+' '+studentName(i.studentId)).toLowerCase().includes(query.toLowerCase()))} bookName={bookName} studentName={studentName} onReturn={returnBook}/></div></>}

        {page==='Overdue Books'&&<div className="panel table-panel"><div className="panel-head"><div><h3>Overdue follow-up</h3><p>Books whose due date has passed</p></div><AlertTriangle size={18} className="muted-icon"/></div><IssueTable issues={overdue} bookName={bookName} studentName={studentName} onReturn={returnBook}/>{overdue.length===0&&<Empty text="Wonderful! No overdue books right now."/ >}</div>}

        {page==='Reports'&&<div className="content-grid"><div className="panel chart-panel"><div className="panel-head"><div><h3>Collection by category</h3><p>Number of book titles</p></div></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={['Fiction','Science','Classic','Biography','Self Growth'].map(c=>({category:c,count:books.filter(b=>b.category===c).length}))}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e9e6df"/><XAxis dataKey="category" axisLine={false} tickLine={false} tick={{fill:'#8c8d91',fontSize:10}}/><YAxis allowDecimals={false} axisLine={false} tickLine={false}/><Tooltip/><Bar dataKey="count" fill="#b99863" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div></div><div className="panel collection-panel"><div className="panel-head"><div><h3>Quick summary</h3><p>Current library totals</p></div></div><div className="report-stat"><span>Total titles</span><b>{books.length}</b></div><div className="report-stat"><span>Total copies</span><b>{totalCopies}</b></div><div className="report-stat"><span>Registered students</span><b>{students.length}</b></div><div className="report-stat"><span>Overdue records</span><b>{overdue.length}</b></div><button className="primary-button full" onClick={()=>{const csv=['Title,Author,Category,ISBN,Copies,Available',...books.map(b=>[b.title,b.author,b.category,b.isbn,b.copies,b.available].map(v=>`"${String(v).replaceAll('"','""')}"`).join(','))].join('\\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='smartschool-book-inventory.csv';a.click();URL.revokeObjectURL(a.href);flash('Inventory CSV downloaded')}>Download inventory CSV</button></div></div>}
      </div>
      <footer className="footer"><span>© 2026 SmartSchool Library</span><span>Thoughtfully built for better learning <span className="gold-heart">✦</span></span></footer>
    </main>

    {showBook&&<Modal title={editingBook?'Edit book details':'Add a new book'} onClose={()=>setShowBook(false)}><form onSubmit={submitBook} className="form-stack"><Field label="Book title"><input required value={bookForm.title} onChange={e=>setBookForm({...bookForm,title:e.target.value})} placeholder="e.g. The Alchemist"/></Field><Field label="Author"><input required value={bookForm.author} onChange={e=>setBookForm({...bookForm,author:e.target.value})} placeholder="Author name"/></Field><div className="form-row"><Field label="Category"><select value={bookForm.category} onChange={e=>setBookForm({...bookForm,category:e.target.value})}>{['Fiction','Science','Classic','Biography','Self Growth','History','Technology','Other'].map(x=><option>{x}</option>)}</select></Field><Field label="Total copies"><input type="number" min="1" required value={bookForm.copies} onChange={e=>setBookForm({...bookForm,copies:e.target.value})}/></Field></div><Field label="ISBN"><input value={bookForm.isbn} onChange={e=>setBookForm({...bookForm,isbn:e.target.value})} placeholder="ISBN number"/></Field><div className="modal-actions"><button type="button" className="secondary-button" onClick={()=>setShowBook(false)}>Cancel</button><button className="primary-button">{editingBook?'Save changes':'Add to catalogue'}</button></div></form></Modal>}
    {showStudent&&<Modal title="Register a student" onClose={()=>setShowStudent(false)}><form onSubmit={submitStudent} className="form-stack"><Field label="Student name"><input required value={studentForm.name} onChange={e=>setStudentForm({...studentForm,name:e.target.value})} placeholder="Full name"/></Field><div className="form-row"><Field label="Roll number"><input required value={studentForm.roll} onChange={e=>setStudentForm({...studentForm,roll:e.target.value})} placeholder="ST-1027"/></Field><Field label="Class / Section"><input required value={studentForm.className} onChange={e=>setStudentForm({...studentForm,className:e.target.value})} placeholder="10-A"/></Field></div><Field label="Email (optional)"><input type="email" value={studentForm.email} onChange={e=>setStudentForm({...studentForm,email:e.target.value})} placeholder="student@school.edu"/></Field><div className="modal-actions"><button type="button" className="secondary-button" onClick={()=>setShowStudent(false)}>Cancel</button><button className="primary-button">Register student</button></div></form></Modal>}
    {showIssue&&<Modal title="Issue a book" onClose={()=>setShowIssue(false)}><form onSubmit={submitIssue} className="form-stack"><Field label="Select book"><select required value={issueForm.bookId} onChange={e=>setIssueForm({...issueForm,bookId:e.target.value})}><option value="">Choose an available book</option>{books.filter(b=>b.available>0).map(b=><option value={b.id}>{b.title} ({b.available} available)</option>)}</select></Field><Field label="Select student"><select required value={issueForm.studentId} onChange={e=>setIssueForm({...issueForm,studentId:e.target.value})}><option value="">Choose a student</option>{students.map(s=><option value={s.id}>{s.name} · {s.roll}</option>)}</select></Field><Field label="Due date"><input type="date" required min={today()} value={issueForm.dueDate} onChange={e=>setIssueForm({...issueForm,dueDate:e.target.value})}/></Field><div className="modal-actions"><button type="button" className="secondary-button" onClick={()=>setShowIssue(false)}>Cancel</button><button className="primary-button">Confirm issue</button></div></form></Modal>}
    {notice&&<div className="toast"><CircleCheck size={17}/>{notice}</div>}
  </div>;
}

function Stat({icon:Icon,label,value,note,tone}){return <div className="stat-card"><div className={`stat-icon ${tone}`}><Icon size={18}/></div><span>{label}</span><strong>{value}</strong><small>{note}</small></div>}
function Field({label,children}){return <label className="field"><span>{label}</span>{children}</label>}
function Modal({title,children,onClose}){return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><div className="modal"><div className="modal-head"><div><span className="eyebrow">SMARTSCHOOL LIBRARY</span><h2>{title}</h2></div><button onClick={onClose} className="icon-button"><X size={18}/></button></div>{children}</div></div>}
function Empty({text}){return <div className="empty-state"><BookOpen size={25}/><p>{text}</p></div>}
function IssueTable({issues,bookName,studentName,onReturn}){return <div className="table-scroll"><table><thead><tr><th>BOOK</th><th>STUDENT</th><th>ISSUED ON</th><th>DUE DATE</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>{issues.map(i=><tr key={i.id}><td><div className="book-cell"><div className="mini-book"><BookOpen size={15}/></div><b>{bookName(i.bookId)}</b></div></td><td>{studentName(i.studentId)}</td><td>{i.issueDate}</td><td>{i.dueDate}</td><td><span className={`status ${i.status==='Returned'?'returned':i.dueDate<today()&&i.status!=='Returned'?'overdue':'issued'}`}>{i.status==='Returned'?'Returned':i.dueDate<today()?'Overdue':'Issued'}</span></td><td>{i.status!=='Returned'?<button className="return-button" onClick={()=>onReturn(i)}><RotateCcw size={13}/> Return</button>:<span className="muted">—</span>}</td></tr>)}</tbody></table>{issues.length===0&&<Empty text="No circulation records to show."/ >}</div>}

export default App;