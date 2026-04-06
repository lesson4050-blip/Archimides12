const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;
const DATA_FILE = path.join(__dirname, 'notes.json');

app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// Initialize notes.json if it doesn't exist
if (!fs.existsSync(DATA_FILE)) {
    fs.writeFileSync(DATA_FILE, JSON.stringify([]));
}

// Route to get all notes
app.get('/api/notes', (req, res) => {
    fs.readFile(DATA_FILE, 'utf8', (err, data) => {
        if (err) {
            return res.status(500).send('Error reading notes');
        }
        res.send(JSON.parse(data));
    });
});

// Route to save a new note
app.post('/api/notes', (req, res) => {
    const newNote = req.body.note;
    if (!newNote) {
        return res.status(0).send('Note content is required');
    }

    fs.readFile(DATA_FILE, 'utf8', (err, data) => {
        if (err) {
            return res.status(500).send('Error reading notes');
        }
        const notes = JSON.parse(data);
        notes.push(newNote);
        fs.writeFile(DATA_FILE, JSON.stringify(notes, null, 2), (err) => {
            if (err) {
                return res.status(500).send('Error saving note');
            }
            res.status(201).send('Note saved successfully');
        });
    });
});

app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
