# ExamGraph — Full Source (React + Vite + Flask)

A local, database-free examination timetable generator. It uses a conflict graph and the DSatur graph-colouring algorithm.

## Features
- Dashboard summary
- Course management (add/delete)
- Student-course registrations (add/delete)
- CSV import for courses and registrations
- Conflict graph view
- DSatur timetable generation
- Session/date settings
- Timetable validation and display
- CSV and JSON exports
- In-memory data; no SQL/NoSQL database

## Run on Windows

### 1. Backend
Open a terminal in `backend`:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The API runs at `http://127.0.0.1:5000`.

### 2. Frontend
Open a second terminal in `frontend`:

```powershell
npm install
npm run dev
```

Open the Vite URL shown in the terminal (usually `http://localhost:5173`).

Keep both terminals running.

## CSV formats

`courses.csv`
```csv
code,name,program,duration
MAT101,Mathematics,General,2
```

`registrations.csv`
```csv
student_id,student_name,courses
S001,Student 1,"MAT101,PHY101"
```

The registration importer also accepts one course per row:
```csv
student_id,course_code
S001,MAT101
S001,PHY101
```

## Notes
- Data is stored in memory and resets when the Flask server restarts. Export JSON if you want to keep a copy.
- Each course is a vertex. Two courses are connected if at least one student is registered in both.
- DSatur repeatedly chooses the uncoloured vertex with the highest saturation degree, then highest graph degree, then alphabetically smallest course code.
- Colors map to available sessions. If there are not enough sessions, the API reports which courses could not be placed.
