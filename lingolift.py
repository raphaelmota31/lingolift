import PyPDF2
from googletrans import Translator
try:
    from translate import Translator as FallbackTranslator
except ImportError:
    FallbackTranslator = None
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from threading import Thread
import time
import re
import json
import queue
import sys
import unicodedata

class PDFTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LingoLift: PDF Translator")
        self.root.geometry("700x550")
        
        # Prevent multiple instances
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Queue for thread-safe GUI updates
        self.gui_queue = queue.Queue()
        
        # Variables
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.language_code = tk.StringVar(value="es")
        self.progress = tk.DoubleVar()
        self.status = tk.StringVar(value="Ready")
        self.use_fallback = tk.BooleanVar(value=False)
        self.resume_translation = tk.BooleanVar(value=False)
        
        # Language options
        self.languages = {
            'Spanish': 'es',
            'French': 'fr',
            'German': 'de',
            'Italian': 'it',
            'Portuguese': 'pt',
            'Russian': 'ru',
            'Chinese': 'zh-cn',
            'Japanese': 'ja',
            'Arabic': 'ar',
            'Hindi': 'hi',
            'English': 'en'
        }
        
        # Create UI
        self.create_widgets()
        
        # Start periodic queue check
        self.root.after(100, self.process_gui_queue)
        
        # State variables
        self.is_running = False
        self.cancel_requested = False
        self.translation_thread = None
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input PDF
        ttk.Label(main_frame, text="Input PDF:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        ttk.Entry(main_frame, textvariable=self.input_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)
        
        # Output PDF
        ttk.Label(main_frame, text="Output PDF:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        ttk.Entry(main_frame, textvariable=self.output_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)
        
        # Language selection
        ttk.Label(main_frame, text="Target Language:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        language_menu = ttk.Combobox(main_frame, textvariable=self.language_code, 
                                   values=list(self.languages.values()), width=47)
        language_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Advanced Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky='we')
        
        if FallbackTranslator:
            ttk.Checkbutton(options_frame, text="Use Alternative Translator (for large files)", 
                           variable=self.use_fallback).pack(anchor='w')
        
        ttk.Checkbutton(options_frame, text="Resume Previous Translation", 
                       variable=self.resume_translation).pack(anchor='w')
        
        # Progress bar
        ttk.Label(main_frame, text="Progress:").grid(row=4, column=0, padx=5, pady=5, sticky='e')
        ttk.Progressbar(main_frame, variable=self.progress, maximum=100).grid(
            row=4, column=1, padx=5, pady=5, sticky='we')
        
        # Status
        ttk.Label(main_frame, text="Status:").grid(row=5, column=0, padx=5, pady=5, sticky='e')
        status_label = ttk.Label(main_frame, textvariable=self.status, wraplength=450)
        status_label.grid(row=5, column=1, padx=5, pady=5, sticky='w')
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=10)
        
        self.translate_btn = ttk.Button(btn_frame, text="Translate PDF", command=self.start_translation)
        self.translate_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.cancel_operation, state='disabled')
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Configure grid
        main_frame.columnconfigure(1, weight=1)
    
    def process_gui_queue(self):
        """Process all pending GUI update requests from the queue"""
        try:
            while True:
                task = self.gui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_gui_queue)
    
    def safe_gui_update(self, func, *args, **kwargs):
        """Schedule a GUI update to be executed in the main thread"""
        self.gui_queue.put(lambda: func(*args, **kwargs))
    
    def browse_input(self):
        filename = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filename:
            prev_input = self.input_path.get()
            self.input_path.set(filename)

            base, _ = os.path.splitext(filename)
            new_output = f"{base}_translated_by_pdf_translator.pdf"

            prev_base, _ = os.path.splitext(prev_input)
            prev_auto_output = f"{prev_base}_translated_by_pdf_translator.pdf"

            if not self.output_path.get() or self.output_path.get() == prev_auto_output:
                self.output_path.set(new_output)

    def browse_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if filename:
            self.output_path.set(filename)
    
    def start_translation(self):
        if self.is_running:
            return
            
        if not self.input_path.get():
            self.safe_gui_update(messagebox.showerror, "Error", "Please select an input PDF file")
            return
            
        if not self.output_path.get():
            self.safe_gui_update(messagebox.showerror, "Error", "Please select an output PDF file")
            return
            
        # Reset state
        self.cancel_requested = False
        self.is_running = True
        
        # Update UI
        self.safe_gui_update(self.translate_btn.configure, state='disabled')
        self.safe_gui_update(self.cancel_btn.configure, state='normal')
        self.safe_gui_update(self.status.set, "Initializing...")
        self.safe_gui_update(self.progress.set, 0)
        
        # Start translation thread
        self.translation_thread = Thread(target=self.process_translation, daemon=True)
        self.translation_thread.start()
    
    def cancel_operation(self):
        if self.is_running:
            self.cancel_requested = True
            self.safe_gui_update(self.status.set, "Cancelling...")
        else:
            self.on_close()
    
    def on_close(self):
        """Handle window close event"""
        if self.is_running and self.translation_thread.is_alive():
            self.cancel_requested = True
            self.safe_gui_update(self.status.set, "Finishing current task...")
            self.translation_thread.join(timeout=2)
        self.root.destroy()
        sys.exit(0)
    
    def process_translation(self):
        try:
            # Step 1: Extract text
            self.safe_gui_update(self.status.set, "Extracting text from PDF...")
            original_text = self.extract_text_from_pdf(self.input_path.get())
            if self.cancel_requested:
                self.safe_gui_update(self.reset_ui)
                return
                
            # Step 2: Translate text
            self.safe_gui_update(self.status.set, "Translating text...")
            translated_text = self.translate_large_text(
                original_text, 
                self.language_code.get(),
                self.use_fallback.get(),
                self.resume_translation.get(),
                os.path.splitext(self.output_path.get())[0] + "_progress.json"
            )
            if self.cancel_requested:
                self.safe_gui_update(self.reset_ui)
                return
                
            # Step 3: Create new PDF
            self.safe_gui_update(self.status.set, "Generating translated PDF...")
            self.create_pdf_from_text(translated_text, self.output_path.get())
            if self.cancel_requested:
                self.safe_gui_update(self.reset_ui)
                return
                
            # Success
            self.safe_gui_update(self.progress.set, 100)
            self.safe_gui_update(self.status.set, "Translation complete!")
            self.safe_gui_update(self.output_path.set, self.output_path.get())
            self.safe_gui_update(self.output_path.set, self.output_path.get())
            self.safe_gui_update(
                lambda: messagebox.showinfo(
                    "Success", 
                    f"PDF successfully translated and saved to:\n{self.output_path.get()}"
                )
            )
            
        except Exception as e:
            self.safe_gui_update(self.status.set, f"Error: {str(e)}")
            error_message = str(e)  # Capture error message in local variable
            self.safe_gui_update(
                lambda: messagebox.showerror("Error", f"An error occurred:\n{error_message}")
            )
        finally:
            self.safe_gui_update(self.reset_ui)
    
    def reset_ui(self):
        """Reset UI to ready state"""
        self.is_running = False
        self.progress.set(0)
        self.translate_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text using pdfplumber for better formatting"""
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                if self.cancel_requested:
                    return ""
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
                self.safe_gui_update(self.progress.set, 25 * (i + 1) / total_pages)
                self.safe_gui_update(self.status.set, f"Extracting page {i+1}/{total_pages}...")
        return text.strip()
    
    def translate_large_text(self, text, dest_language, use_fallback=False, resume=False, progress_file=None):
        """Advanced translation with progress saving and large text handling"""
        # Initialize translator
        if use_fallback and FallbackTranslator:
            translator = FallbackTranslator(to_lang=dest_language)
            chunk_size = 5000  # Fallback typically has higher limits
        else:
            translator = Translator()
            chunk_size = 1000  # Smaller chunks for better Hindi handling
            # Set service URLs and parameters for better Hindi support
            translator.raise_Exception = True
            translator.service_urls = [
                'translate.google.com',
                'translate.google.co.in',
            ]
            # Force UTF-8 encoding for Hindi
            import sys
            if sys.stdout.encoding != 'utf-8':
                sys.stdout.reconfigure(encoding='utf-8')
            
        # Load previous progress if resuming
        translated_parts = []
        last_processed = 0
        
        if resume and progress_file and os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
                    translated_parts = progress_data.get('parts', [])
                    last_processed = progress_data.get('last_processed', 0)
                    self.safe_gui_update(self.status.set, f"Resuming from position {last_processed}")
            except Exception as e:
                self.safe_gui_update(
                    lambda: messagebox.showwarning(
                        "Warning", 
                        f"Could not load progress file: {str(e)}"
                    )
                )
        
        # Split text into logical chunks
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        if not paragraphs:
            return ""
            
        total_chars = sum(len(p) for p in paragraphs)
        processed_chars = 0
        translated_text = []
        
        for i, para in enumerate(paragraphs):
            if self.cancel_requested:
                return ""
                
            # Skip already processed paragraphs when resuming
            if resume and processed_chars < last_processed:
                processed_chars += len(para)
                continue
                
            try:
                # Split long paragraphs into smaller chunks if needed
                if len(para) > chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    current_chunk = ""
                    
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) > chunk_size:
                            # Translate current chunk
                            translated = self.translate_chunk(
                                current_chunk, translator, dest_language, use_fallback)
                            translated_text.append(translated)
                            current_chunk = sentence
                            
                            # Save progress
                            processed_chars += len(current_chunk)
                            self.save_progress(progress_file, translated_text, processed_chars)
                        else:
                            current_chunk += " " + sentence if current_chunk else sentence
                    
                    # Translate remaining chunk
                    if current_chunk:
                        translated = self.translate_chunk(
                            current_chunk, translator, dest_language, use_fallback)
                        translated_text.append(translated)
                        processed_chars += len(current_chunk)
                else:
                    # Translate entire paragraph
                    translated = self.translate_chunk(para, translator, dest_language, use_fallback)
                    translated_text.append(translated)
                    processed_chars += len(para)
                
                # Update progress (25-75% for translation)
                progress = 25 + 50 * (processed_chars / total_chars)
                self.safe_gui_update(self.progress.set, progress)
                self.safe_gui_update(self.status.set, f"Translating: {processed_chars}/{total_chars} characters")
                
                # Save progress periodically
                if i % 5 == 0:
                    self.save_progress(progress_file, translated_text, processed_chars)
                    
            except Exception as e:
                print(f"Error translating paragraph: {str(e)}")
                translated_text.append(para)  # Keep original if translation fails
        
        # Clean up progress file
        if progress_file and os.path.exists(progress_file):
            try:
                os.remove(progress_file)
            except:
                pass
                
        return '\n\n'.join(translated_text)
    
    def translate_chunk(self, text, translator, dest_language, use_fallback):
        """Translate a single chunk with enhanced Hindi support and error handling"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        # Pre-process text
        try:
            text = text.strip()
            if not text:
                return ""
            
            # Ensure proper encoding and handle potential encoding issues
            text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            
            # Remove control characters but keep emojis/symbols
            text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
            text = unicodedata.normalize('NFC', text)
        except Exception as e:
            print(f"Warning: Text preprocessing error - {str(e)}")
            return text  # Return original text if preprocessing fails
        
        for attempt in range(max_retries):
            try:
                if use_fallback and isinstance(translator, FallbackTranslator):
                    translated = translator.translate(text)
                else:
                    try:
                        # Add language detection with error handling
                        detected = translator.detect(text)
                        src_lang = detected.lang if detected and hasattr(detected, 'lang') else 'auto'
                    except:
                        src_lang = 'auto'  # Fallback to auto detection
                    
                    result = translator.translate(text, src=src_lang, dest=dest_language)
                    translated = result.text if result and hasattr(result, 'text') else text
                
                # Post-process Hindi text with error handling
                if dest_language.lower() in ['hi', 'hin', 'hindi'] and translated:
                    try:
                        # Add proper spacing after Hindi punctuation
                        translated = re.sub(r'([।॥])', r'\1 ', translated)
                        # Normalize Hindi characters
                        translated = unicodedata.normalize('NFC', translated)
                        # Remove any invalid or control characters
                        translated = ''.join(char for char in translated if unicodedata.category(char)[0] != 'C')
                    except Exception as e:
                        print(f"Warning: Hindi post-processing error - {str(e)}")
                
                return translated if translated else text
            except Exception as e:
                print(f"Translation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    print(f"All translation attempts failed for text: {text[:100]}...")
                    return text  # Return original text after all retries fail
                time.sleep(retry_delay * (attempt + 1))
    
    def save_progress(self, progress_file, translated_parts, last_processed):
        """Save translation progress to file"""
        if not progress_file:
            return
            
        try:
            progress_data = {
                'parts': translated_parts,
                'last_processed': last_processed,
                'timestamp': time.time()
            }
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f)
        except Exception as e:
            print(f"Warning: Could not save progress - {str(e)}")
    
    def create_pdf_from_text(self, text, output_path):
        """Create PDF with basic formatting for Hindi"""
        if self.cancel_requested:
            return
            
        # Create directory if needed
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        # Create PDF canvas directly
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Language to font mapping
        language_fonts = {
            'hi': "Mangal",
            'en': "SegoeUIEmoji",
            'fr': "Arial",
            'de': "Arial",
            'es': "Arial",
            'ru': "Arial",
            'zh-cn': "Arial",
            'ja': "Arial",
            'ar': "Arial"
        }

        # Set default font name from mapping
        font_name = language_fonts.get(self.language_code.get().lower(), "Helvetica")

        # Detect font path (override for known fonts)
        font_paths = {
            "Mangal": os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts/Mangal.ttf"),
            "Arial": "C:/Windows/Fonts/arial.ttf",
            "SegoeUIEmoji": "C:/Windows/Fonts/seguiemj.ttf",
            "ArialUnicodeMS": "C:/Windows/Fonts/arialuni.ttf"
        }

        font_path = font_paths.get(font_name, None)

        if font_path and os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                print(f"[INFO] Registered font: {font_name}")
            except Exception as e:
                print(f"[ERROR] Failed to register font {font_name}: {e}")
                font_name = "Helvetica"
        else:
            print(f"[WARNING] Font file not found for: {font_name}. Falling back to Helvetica.")
            font_name = "Helvetica"

        try:
            c.setFont(font_name, 12)
        except Exception as e:
            print(f"[ERROR] Failed to set font {font_name}: {e}")
            c.setFont("Helvetica", 12)
    
        except Exception as e:
            print(f"[ERROR] Failed to set font {font_name}: {e}")
            c.setFont("Helvetica", 12)
        except Exception as e:
            print(f"Warning: Failed to set font {font_name}: {str(e)}")
            c.setFont('Helvetica', 12)  # Emergency fallback
        
        # Split text into paragraphs
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        total_paragraphs = len(paragraphs)
        
        y = height - 50  # Start from top with margin
        for i, para in enumerate(paragraphs):
            if self.cancel_requested:
                return
                
            # Update progress (75-100% for PDF creation)
            progress = 75 + 25 * (i + 1) / total_paragraphs
            self.safe_gui_update(self.progress.set, progress)
            self.safe_gui_update(self.status.set, f"Formatting PDF: {i+1}/{total_paragraphs}")
            
            # Wrap text to fit page width with better Hindi support
            try:
                # Split text into words, preserving Hindi word boundaries
                words = []
                current_word = []
                
                for char in para:
                    if char.isspace():
                        if current_word:
                            words.append(''.join(current_word))
                            current_word = []
                        continue
                    current_word.append(char)
                
                if current_word:
                    words.append(''.join(current_word))
                
                lines = []
                current_line = []
                
                for word in words:
                    # Skip empty words
                    if not word.strip():
                        continue
                        
                    current_line.append(word)
                    try:
                        line_width = c.stringWidth(' '.join(current_line), font_name, 12)
                    except:
                        # Fallback to estimating width if stringWidth fails
                        line_width = sum(len(w) * 7 for w in current_line)  # Approximate width
                    
                    # Check if line exceeds page width
                    if line_width > width - 100:  # Leave margins
                        if len(current_line) > 1:
                            # Add all words except the last one to lines
                            lines.append(' '.join(current_line[:-1]))
                            current_line = [current_line[-1]]
                        else:
                            # If single word is too long, force split it
                            word_to_split = current_line[0]
                            split_point = len(word_to_split) // 2
                            lines.append(word_to_split[:split_point] + '-')
                            current_line = [word_to_split[split_point:]]
                
                # Add remaining words as last line
                if current_line:
                    lines.append(' '.join(current_line))
            except Exception as e:
                print(f"Warning: Text wrapping failed: {str(e)}")
                # Fallback to simple line splitting
                lines = [para]
            
            # Draw lines with error handling
            for line in lines:
                if y < 50:  # Bottom margin
                    c.showPage()
                    y = height - 50
                    try:
                        c.setFont(font_name, 12)
                    except:
                        c.setFont('Helvetica', 12)
                
                try:
                    # Normalize and clean the text
                    clean_line = unicodedata.normalize('NFC', line)
                    clean_line = ''.join(char for char in clean_line if unicodedata.category(char)[0] != 'C')
                    
                    # Center align text
                    try:
                        text_width = c.stringWidth(clean_line, font_name, 12)
                    except:
                        # Fallback to estimating width
                        text_width = len(clean_line) * 7  # Approximate width
                    
                    x = (width - text_width) / 2
                    
                    # Try to draw with main font
                    try:
                        c.drawString(x, y, clean_line)
                    except:
                        # Fallback to drawing with Helvetica
                        c.setFont('Helvetica', 12)
                        c.drawString(x, y, clean_line)
                except Exception as e:
                    print(f"Warning: Failed to draw line: {str(e)}")
                    # Try to draw with basic ASCII representation as last resort
                    try:
                        ascii_line = line.encode('ascii', 'replace').decode('ascii')
                        c.setFont('Helvetica', 12)
                        c.drawString(x, y, ascii_line)
                    except:
                        pass  # Skip line if all attempts fail
                
                y -= 20  # Line spacing
            
            y -= 10  # Paragraph spacing
        
        c.save()
        


def main():
    # Create single instance check
    try:
        from tendo import singleton
        me = singleton.SingleInstance()
    except ImportError:
        pass  # No single instance enforcement if tendo not available
    
    # Create root window with theme if available
    try:
        from ttkthemes import ThemedTk
        root = ThemedTk(theme="arc")
    except ImportError:
        root = tk.Tk()
        
    app = PDFTranslatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()