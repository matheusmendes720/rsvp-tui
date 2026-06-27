"""Note management for reading annotations."""

import json
import logging
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models import Note
from ..logging_ import telemetry

log = logging.getLogger(__name__)


class NoteManager:
    """Manages notes linked to reading positions."""
    
    def __init__(self, notes_dir: Optional[Path] = None):
        from ..models import Config
        if notes_dir is None:
            config = Config.load()
            notes_dir = config.notes_dir
        
        self.notes_dir = notes_dir
        self.notes_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_notes_file(self, book_id: str) -> Path:
        """Get the notes file path for a book."""
        book_notes_dir = self.notes_dir / book_id
        book_notes_dir.mkdir(exist_ok=True)
        return book_notes_dir / "notes.json"
    
    def _load_notes_for_book(self, book_id: str) -> List[Note]:
        """Load all notes for a book."""
        notes_file = self._get_notes_file(book_id)
        
        if not notes_file.exists():
            return []
        
        try:
            with open(notes_file) as f:
                data = json.load(f)
            return [Note.from_dict(n) for n in data]
        except (json.JSONDecodeError, KeyError):
            return []
    
    def _save_notes_for_book(self, book_id: str, notes: List[Note]) -> None:
        """Save notes for a book."""
        notes_file = self._get_notes_file(book_id)
        
        with open(notes_file, "w") as f:
            json.dump([n.to_dict() for n in notes], f, indent=2, default=str)
    
    def create_note(
        self,
        book_id: str,
        word_index: int,
        chapter_index: int,
        content: str,
        tags: Optional[List[str]] = None,
        word_context: str = "",
    ) -> Note:
        """Create a new note at a specific position."""
        note = Note(
            id=f"note_{uuid.uuid4().hex[:12]}",
            book_id=book_id,
            word_index=word_index,
            chapter_index=chapter_index,
            content=content,
            tags=tags or [],
            word_context=word_context,
        )

        notes = self._load_notes_for_book(book_id)
        notes.append(note)
        self._save_notes_for_book(book_id, notes)

        log.info(
            "note.create: book_id=%s note_id=%s word_index=%d",
            book_id,
            note.id,
            word_index,
        )
        telemetry.note_created(book_id=book_id, note_id=note.id, word_index=word_index)

        return note
    
    def get_notes_for_book(self, book_id: str) -> List[Note]:
        """Get all notes for a book."""
        return self._load_notes_for_book(book_id)
    
    def get_notes_for_position(
        self,
        book_id: str,
        word_index: int,
        context_window: int = 50,
    ) -> List[Note]:
        """Get notes near a specific position."""
        notes = self._load_notes_for_book(book_id)
        
        return [
            n for n in notes
            if abs(n.word_index - word_index) <= context_window
        ]
    
    def update_note(self, book_id: str, note_id: str, content: str) -> Optional[Note]:
        """Update an existing note."""
        notes = self._load_notes_for_book(book_id)
        
        for note in notes:
            if note.id == note_id:
                note.content = content
                note.updated_at = datetime.now()
                self._save_notes_for_book(book_id, notes)
                return note
        
        return None
    
    def delete_note(self, book_id: str, note_id: str) -> bool:
        """Delete a note."""
        notes = self._load_notes_for_book(book_id)

        original_count = len(notes)
        notes = [n for n in notes if n.id != note_id]

        if len(notes) < original_count:
            self._save_notes_for_book(book_id, notes)
            log.info("note.delete: book_id=%s note_id=%s", book_id, note_id)
            telemetry.note_deleted(book_id=book_id, note_id=note_id)
            return True

        return False
    
    def export_notes_to_markdown(self, book_id: str, book_title: str) -> Path:
        """Export all notes for a book to Markdown."""
        notes = self._load_notes_for_book(book_id)
        notes.sort(key=lambda n: n.word_index)
        
        output_file = self.notes_dir / f"{book_id}_notes.md"
        
        with open(output_file, "w") as f:
            f.write(f"# Notes: {book_title}\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("---\n\n")
            
            for note in notes:
                f.write(note.to_markdown())
                f.write("\n")
        
        return output_file
    
    def get_note_count(self, book_id: str) -> int:
        """Get number of notes for a book."""
        return len(self._load_notes_for_book(book_id))
    
    def search_notes(self, book_id: str, query: str) -> List[Note]:
        """Search notes by content."""
        notes = self._load_notes_for_book(book_id)
        query = query.lower()
        
        return [
            n for n in notes
            if query in n.content.lower() or any(query in t.lower() for t in n.tags)
        ]
    
    def get_all_tags(self, book_id: str) -> List[str]:
        """Get all unique tags for a book."""
        notes = self._load_notes_for_book(book_id)
        tags = set()
        
        for note in notes:
            tags.update(note.tags)
        
        return sorted(list(tags))
