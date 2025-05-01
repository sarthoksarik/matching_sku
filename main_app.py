# File: main_app.py
import tkinter as tk
from tkinter import (
    scrolledtext,
    messagebox,
    simpledialog,
    Listbox,
    Toplevel,
    Frame,
    Scrollbar,
    END,
    SINGLE,
    Button,
    Label,
    Entry,
    Scale,
    IntVar,
    StringVar,
    Radiobutton,
    Frame,
    LabelFrame,
)  # Added LabelFrame
import database as db
from thefuzz import process
import os  # For environment variables and path handling
import sys  # To detect if running as frozen executable
import google.generativeai as genai

# --- Constants ---
NO_MATCH_TEXT = "--- NO MATCH FOUND ---"
DEFAULT_THRESHOLD = 70
ENGINE_FUZZY = "fuzzy"
ENGINE_GEMINI = "gemini"
GEMINI_API_ENV_VAR = "GEMINI_API_KEY"
API_KEY_FILENAME = "api_key.txt"  # Name of the key file
GEMINI_MODEL_NAME = "gemini-1.5-flash"


# --- Matching Logic ---
# find_best_sku_match_fuzzy remains the same
def find_best_sku_match_fuzzy(product_name, sku_list, threshold):
    if not product_name or not sku_list:
        return NO_MATCH_TEXT
    try:
        result = process.extractOne(str(product_name), sku_list)
        if result:
            best_match, score = result
            if score >= threshold:
                return best_match
            else:
                return NO_MATCH_TEXT
        else:
            return NO_MATCH_TEXT
    except Exception as e:
        print(f"Error during fuzzy matching for '{product_name}': {e}")
        return "--- ERROR DURING FUZZY MATCH ---"


# find_best_sku_match_gemini remains the same
def find_best_sku_match_gemini(product_name, sku_list, api_key):
    if not product_name or not sku_list:
        return NO_MATCH_TEXT
    if not api_key:
        print("Error: Gemini API key not provided.")
        return "--- ERROR: MISSING API KEY ---"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        prompt = f"""Analyze the following product name and list of SKUs. Identify the single best matching SKU from the list provided.

Product Name: "{product_name}"

Available SKUs:
{chr(10).join(f"- {sku}" for sku in sku_list)}

Your Task: Respond with ONLY the single best matching SKU name exactly as it appears in the 'Available SKUs' list.
If none of the SKUs in the list are a suitable match for the product name, respond with the exact text: NO MATCH
Do not include any explanations, introductions, or formatting other than the single matching SKU or "NO MATCH".
"""
        response = model.generate_content(prompt)
        try:
            gemini_result = response.text.strip()
            if gemini_result == "NO MATCH":
                return NO_MATCH_TEXT
            elif gemini_result in sku_list:
                return gemini_result
            else:
                print(
                    f"Warning: Gemini returned text ('{gemini_result}') not exactly in SKU list for product '{product_name}'. Treating as no match."
                )
                return NO_MATCH_TEXT
        except ValueError:
            print(
                f"Warning: Gemini response blocked or empty for product '{product_name}'. Response parts: {response.parts}"
            )
            return "--- GEMINI RESPONSE BLOCKED/EMPTY ---"
        except Exception as e_parse:
            print(f"Error parsing Gemini response for '{product_name}': {e_parse}")
            return "--- ERROR PARSING GEMINI RESPONSE ---"
    except Exception as e_api:
        print(f"Error during Gemini API call for '{product_name}': {e_api}")
        if "API key not valid" in str(e_api):
            return "--- ERROR: INVALID API KEY ---"
        return "--- ERROR DURING GEMINI API CALL ---"


# --- GUI Classes ---


# SkuManagerWindow class remains IDENTICAL
class SkuManagerWindow(Toplevel):
    """Window for managing the SKUs in the database."""

    # ... (Keep the exact code from the previous response) ...
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage SKUs")
        self.geometry("450x480")
        self.transient(parent)
        self.grab_set()

        self.add_frame = Frame(self)
        self.add_label = Label(self.add_frame, text="New SKU:")
        self.sku_entry = Entry(self.add_frame, width=30)
        self.add_button = Button(self.add_frame, text="Add SKU", command=self.add_sku)

        self.list_frame = Frame(self)
        self.list_label = Label(self.list_frame, text="Current SKUs:")
        self.scrollbar = Scrollbar(self.list_frame, orient=tk.VERTICAL)
        self.sku_listbox = Listbox(
            self.list_frame,
            yscrollcommand=self.scrollbar.set,
            selectmode=SINGLE,
            width=50,
            height=12,
        )
        self.scrollbar.config(command=self.sku_listbox.yview)

        self.action_button_frame = Frame(self)
        self.edit_button = Button(
            self.action_button_frame,
            text="Edit Selected",
            command=self.edit_selected_sku,
        )
        self.delete_button = Button(
            self.action_button_frame,
            text="Delete Selected",
            command=self.delete_selected_sku,
        )
        self.paste_button = Button(
            self.action_button_frame,
            text="Paste SKUs from Clipboard",
            command=self.paste_skus_from_clipboard,
        )

        self.close_button = Button(self, text="Close", command=self.destroy)

        # --- Layout ---
        self.add_frame.pack(pady=10, padx=10, fill=tk.X)
        self.add_label.pack(side=tk.LEFT, padx=5)
        self.sku_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.list_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        self.list_label.pack(anchor=tk.W)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sku_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.action_button_frame.pack(pady=5, padx=10, fill=tk.X)
        self.edit_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.delete_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.paste_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.close_button.pack(pady=10)

        # --- Initial Population & Bindings ---
        self.refresh_sku_list()
        self.sku_entry.bind("<Return>", lambda event: self.add_sku())
        self.sku_entry.focus_set()

    def refresh_sku_list(self):
        current_selection_index = self.sku_listbox.curselection()
        current_value = None
        if current_selection_index:
            current_value = self.sku_listbox.get(current_selection_index[0])
        self.sku_listbox.delete(0, END)
        skus = db.get_all_skus()
        new_selection_index = None
        for i, sku in enumerate(skus):
            self.sku_listbox.insert(END, sku)
            if sku == current_value:
                new_selection_index = i
        if new_selection_index is not None:
            try:
                self.sku_listbox.select_set(new_selection_index)
                self.sku_listbox.activate(new_selection_index)
                self.sku_listbox.see(new_selection_index)
            except tk.TclError:
                pass

    def add_sku(self):
        new_sku = self.sku_entry.get().strip()
        if not new_sku:
            messagebox.showwarning(
                "Input Error", "Please enter an SKU name.", parent=self
            )
            return
        if db.add_sku(new_sku):
            self.refresh_sku_list()
            self.sku_entry.delete(0, END)
        else:
            messagebox.showerror(
                "Database Error",
                f"Failed to add SKU '{new_sku}'.\nIt might already exist or there was a database issue.",
                parent=self,
            )

    def get_selected_sku(self):
        selected_indices = self.sku_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(
                "Selection Error",
                "Please select an SKU from the list first.",
                parent=self,
            )
            return None
        return self.sku_listbox.get(selected_indices[0])

    def edit_selected_sku(self):
        selected_sku = self.get_selected_sku()
        if selected_sku is None:
            return
        new_name = simpledialog.askstring(
            "Edit SKU",
            f"Enter the new name for SKU:",
            initialvalue=selected_sku,
            parent=self,
        )
        if new_name is not None:
            new_name = new_name.strip()
            if not new_name:
                messagebox.showerror(
                    "Input Error", "New SKU name cannot be empty.", parent=self
                )
                return
            if new_name == selected_sku:
                return
            if db.update_sku(selected_sku, new_name):
                self.refresh_sku_list()
                messagebox.showinfo(
                    "Success", f"SKU updated to '{new_name}'.", parent=self
                )
            else:
                messagebox.showerror(
                    "Update Error",
                    f"Could not update SKU.\nThe new name '{new_name}' might already exist.",
                    parent=self,
                )

    def delete_selected_sku(self):
        selected_sku = self.get_selected_sku()
        if selected_sku is None:
            return
        if messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete SKU:\n'{selected_sku}'?",
            parent=self,
        ):
            if db.delete_sku(selected_sku):
                self.refresh_sku_list()
            else:
                messagebox.showerror(
                    "Database Error",
                    f"Failed to delete SKU '{selected_sku}'. It might have already been deleted.",
                    parent=self,
                )

    def paste_skus_from_clipboard(self):
        try:
            clipboard_content = self.clipboard_get()
        except tk.TclError:
            messagebox.showerror(
                "Clipboard Error",
                "Could not read text data from clipboard.",
                parent=self,
            )
            return
        if not clipboard_content:
            messagebox.showwarning(
                "Clipboard Empty",
                "Clipboard is empty or contains no text.",
                parent=self,
            )
            return
        potential_skus = [
            line.strip() for line in clipboard_content.splitlines() if line.strip()
        ]
        if not potential_skus:
            messagebox.showwarning(
                "No SKUs Found",
                "No valid SKU text found in clipboard data after processing.",
                parent=self,
            )
            return
        added_count = 0
        failed_count = 0
        if not messagebox.askyesno(
            "Confirm Paste",
            f"Found {len(potential_skus)} potential SKUs in clipboard.\n\nExample: '{potential_skus[0]}'\n\nProceed adding them? (Duplicates will be skipped)",
            parent=self,
        ):
            return
        for sku in potential_skus:
            if db.add_sku(sku):
                added_count += 1
            else:
                failed_count += 1
        self.refresh_sku_list()
        summary_message = f"Paste SKUs Report:\n\nSuccessfully Added: {added_count}\nSkipped (Duplicates/Errors): {failed_count}"
        messagebox.showinfo("Paste Complete", summary_message, parent=self)


# --- Main Application Class (MODIFIED) ---
class Application(tk.Tk):
    """Main application class."""

    def __init__(self):
        super().__init__()
        self.title("Product Name to SKU Converter")
        self.geometry("700x620")

        # --- Determine Base Path (for script or frozen executable) ---
        if getattr(sys, "frozen", False):
            # Running as bundled executable (PyInstaller)
            self.base_path = os.path.dirname(sys.executable)
            print(f"Running bundled executable. Base path: {self.base_path}")
        else:
            # Running as script
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            print(f"Running as script. Base path: {self.base_path}")

        # --- Variables ---
        self.all_skus = []
        self._warned_no_skus = False
        self.similarity_threshold = IntVar(value=DEFAULT_THRESHOLD)
        self.engine_choice = StringVar(value=ENGINE_FUZZY)  # Default to fuzzy
        self.api_key_var = StringVar()  # To hold API key from entry

        # --- API Key Loading Logic ---
        self.env_api_key = os.environ.get(GEMINI_API_ENV_VAR)
        self.file_api_key = None
        self.api_key_source = None  # To track where the key was loaded from

        # 1. Check Environment Variable
        if self.env_api_key:
            print(
                f"Info: Found Gemini API key in environment variable {GEMINI_API_ENV_VAR}."
            )
            self.api_key_source = "ENV"
            self.api_key_var.set("Detected in Environment Variable")
        else:
            # 2. Check api_key.txt File
            key_file_path = os.path.join(self.base_path, API_KEY_FILENAME)
            try:
                with open(key_file_path, "r") as f:
                    self.file_api_key = f.readline().strip()
                    if self.file_api_key:
                        print(f"Info: Found Gemini API key in file: {key_file_path}")
                        self.api_key_source = "FILE"
                        self.api_key_var.set(f"Detected in {API_KEY_FILENAME}")
                    else:
                        print(
                            f"Info: API key file '{key_file_path}' found but is empty."
                        )
                        self.api_key_source = None
            except FileNotFoundError:
                print(f"Info: API key file '{key_file_path}' not found.")
                self.api_key_source = None  # Ensure it's None if file not found
            except Exception as e:
                print(f"Error reading API key file '{key_file_path}': {e}")
                self.api_key_source = None

        # 3. GUI Entry - Initial state set later in toggle_controls

        # --- Widgets ---
        # Input Frame (Left)
        input_frame = Frame(self)
        input_label = Label(input_frame, text="Paste Product Names (one per line):")
        self.input_text = scrolledtext.ScrolledText(
            input_frame, height=15, width=40, wrap=tk.WORD
        )

        # Button & Control Frame (Center)
        control_frame = Frame(self)
        self.convert_button = Button(
            control_frame,
            text="Convert >>",
            command=self.perform_conversion,
            width=12,
            height=2,
        )
        self.manage_button = Button(
            control_frame, text="Manage SKUs", command=self.open_sku_manager, width=12
        )

        # -- Engine Selection Frame --
        engine_frame = LabelFrame(control_frame, text="Matching Engine")
        self.fuzzy_radio = Radiobutton(
            engine_frame,
            text="Fuzzy Match",
            variable=self.engine_choice,
            value=ENGINE_FUZZY,
            command=self.toggle_controls,
        )
        self.gemini_radio = Radiobutton(
            engine_frame,
            text="Gemini AI",
            variable=self.engine_choice,
            value=ENGINE_GEMINI,
            command=self.toggle_controls,
        )

        # -- Fuzzy Threshold Controls --
        self.threshold_frame = Frame(control_frame)
        threshold_label = Label(self.threshold_frame, text="Match Sensitivity:")
        self.threshold_value_label = Label(
            self.threshold_frame, textvariable=self.similarity_threshold, width=3
        )
        self.threshold_scale = Scale(
            self.threshold_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.similarity_threshold,
            length=120,
            showvalue=0,
        )

        # -- Gemini API Key Controls --
        self.api_key_frame = Frame(control_frame)
        api_key_label = Label(self.api_key_frame, text="Gemini API Key:")
        self.api_key_entry = Entry(
            self.api_key_frame, textvariable=self.api_key_var, width=20, show="*"
        )
        # Updated info label text
        self.api_key_info_label = Label(
            self.api_key_frame,
            text=f"(Uses ENV > {API_KEY_FILENAME} > Entry)",
            fg="blue",
            cursor="hand2",
        )
        self.api_key_info_label.bind(
            "<Button-1>",
            lambda e: messagebox.showinfo(
                "API Key Info",
                f"API Key Loading Order:\n"
                f"1. Environment variable: {GEMINI_API_ENV_VAR}\n"
                f"2. File in app folder: {API_KEY_FILENAME}\n"
                f"3. Manual entry here (if 1 & 2 not found).\n\n"
                f"Recommendation: Use Option 1 or 2 for better security.",
                parent=self,
            ),
        )

        # Output Frame (Right)
        output_frame = Frame(self)
        output_label = Label(output_frame, text="Matching SKUs:")
        self.output_text = scrolledtext.ScrolledText(
            output_frame, height=15, width=40, wrap=tk.WORD, state=tk.DISABLED
        )

        # --- Layout ---
        input_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        input_label.pack(anchor=tk.W, pady=(0, 5))
        self.input_text.pack(fill=tk.BOTH, expand=True)

        # Layout for Control Frame (Center)
        control_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        self.convert_button.pack(pady=(20, 15))
        self.manage_button.pack(pady=15)
        engine_frame.pack(pady=(20, 10), padx=5, fill=tk.X)
        self.fuzzy_radio.pack(anchor=tk.W)
        self.gemini_radio.pack(anchor=tk.W)
        self.threshold_frame.pack(pady=10, padx=5, fill=tk.X)
        threshold_label.pack(side=tk.LEFT)
        self.threshold_value_label.pack(side=tk.LEFT, padx=2)
        self.threshold_scale.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.api_key_frame.pack(pady=10, padx=5, fill=tk.X)
        api_key_label.pack(anchor=tk.W)
        self.api_key_entry.pack(fill=tk.X, pady=(0, 2))
        self.api_key_info_label.pack(anchor=tk.W)

        output_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        output_label.pack(anchor=tk.W, pady=(0, 5))
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # --- Initialization ---
        self.load_skus()
        self.toggle_controls()  # Set initial UI state

    # MODIFIED toggle_controls
    def toggle_controls(self):
        """Show/hide controls based on selected engine and API key source."""
        selected_engine = self.engine_choice.get()
        if selected_engine == ENGINE_FUZZY:
            self.threshold_frame.pack(pady=10, padx=5, fill=tk.X)
            self.api_key_frame.pack_forget()
        elif selected_engine == ENGINE_GEMINI:
            self.threshold_frame.pack_forget()
            self.api_key_frame.pack(pady=10, padx=5, fill=tk.X)
            # Disable entry if key found in ENV or FILE, enable otherwise
            if self.api_key_source in ["ENV", "FILE"]:
                self.api_key_entry.config(state=tk.DISABLED)
                # Make sure placeholder text reflects the source
                if self.api_key_source == "ENV":
                    self.api_key_var.set("Detected in Environment Variable")
                else:  # Must be FILE
                    self.api_key_var.set(f"Detected in {API_KEY_FILENAME}")
            else:
                # Enable entry, clear placeholder if necessary
                self.api_key_entry.config(state=tk.NORMAL)
                if self.api_key_var.get().startswith("Detected in"):
                    self.api_key_var.set("")
        else:  # Should not happen
            self.threshold_frame.pack_forget()
            self.api_key_frame.pack_forget()

    def load_skus(self):
        """Loads/reloads the list of SKUs from the database into memory."""
        self.all_skus = db.get_all_skus()
        print(f"Loaded {len(self.all_skus)} SKUs into memory.")
        if not self.all_skus and not self._warned_no_skus:
            messagebox.showwarning(
                "No SKUs Loaded",
                "The SKU database is currently empty.\n\nPlease use 'Manage SKUs' to add your official SKU list before converting.",
                parent=self,
            )
            self._warned_no_skus = True

    # MODIFIED perform_conversion
    def perform_conversion(self):
        """Reads input, finds matches using the selected engine, and displays results."""
        selected_engine = self.engine_choice.get()
        print(f"Starting conversion using engine: {selected_engine}")

        input_content = self.input_text.get("1.0", tk.END).strip()
        if not input_content:
            messagebox.showwarning(
                "Input Error",
                "Please paste product names into the input area on the left.",
                parent=self,
            )
            return

        product_names = [
            name.strip() for name in input_content.splitlines() if name.strip()
        ]
        if not product_names:
            messagebox.showwarning(
                "Input Error", "No valid product names found in the input.", parent=self
            )
            return

        self.load_skus()
        if not self.all_skus:
            messagebox.showerror(
                "Error",
                "No SKUs available in the database. Cannot perform conversion.",
                parent=self,
            )
            return

        matched_skus = []
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(
            tk.END,
            f"Processing {len(product_names)} items using {selected_engine}...\n(This may take a while with Gemini)",
        )
        self.output_text.config(state=tk.DISABLED)
        self.update_idletasks()

        # --- Engine-Specific Logic ---
        if selected_engine == ENGINE_FUZZY:
            current_threshold = self.similarity_threshold.get()
            print(f"Using fuzzy threshold: {current_threshold}")
            matched_skus = [
                find_best_sku_match_fuzzy(name, self.all_skus, current_threshold)
                for name in product_names
            ]

        elif selected_engine == ENGINE_GEMINI:
            # --- Determine API Key based on priority ---
            api_key_to_use = None
            if self.api_key_source == "ENV":
                api_key_to_use = self.env_api_key
                print("Using API key from Environment Variable.")
            elif self.api_key_source == "FILE":
                api_key_to_use = self.file_api_key
                print(f"Using API key from {API_KEY_FILENAME}.")
            else:  # No key found in ENV or FILE, try GUI entry
                gui_key = self.api_key_var.get().strip()
                # Check if it's empty or still the placeholder text
                if gui_key and not gui_key.startswith("Detected in"):
                    api_key_to_use = gui_key
                    print("Using API key from GUI entry.")
                else:
                    api_key_to_use = (
                        None  # Explicitly set to None if entry is empty/placeholder
                    )

            # Check if we have a key
            if not api_key_to_use:
                messagebox.showerror(
                    "API Key Error",
                    f"Gemini API Key not found.\nPlease set the {GEMINI_API_ENV_VAR} environment variable, create {API_KEY_FILENAME} in the app folder, or paste the key into the field.",
                    parent=self,
                )
                self.output_text.config(state=tk.NORMAL)
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(
                    tk.END, "Conversion cancelled: Missing API Key."
                )
                self.output_text.config(state=tk.DISABLED)
                return  # Stop processing

            print("Using Gemini AI. API calls can take time...")
            # Process sequentially
            for i, name in enumerate(product_names):
                match_result = find_best_sku_match_gemini(
                    name, self.all_skus, api_key_to_use
                )
                matched_skus.append(match_result)
                if "ERROR: INVALID API KEY" in match_result:
                    messagebox.showerror(
                        "API Key Error",
                        "Gemini API Key seems invalid. Please check the key source (ENV, file, or entry) and try again.",
                        parent=self,
                    )
                    break  # Stop processing
                elif (
                    "ERROR: MISSING API KEY" in match_result
                ):  # Should be caught earlier, but just in case
                    messagebox.showerror(
                        "API Key Error", "Gemini API Key missing.", parent=self
                    )
                    break

            print("Gemini processing finished.")

        # --- Display final results ---
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        if matched_skus:
            self.output_text.insert(tk.END, "\n".join(matched_skus))
        else:
            self.output_text.insert(
                tk.END, "Processing incomplete or no results generated."
            )
        self.output_text.config(state=tk.DISABLED)

    def open_sku_manager(self):
        """Opens the SKU Management window."""
        manager_window = SkuManagerWindow(self)
        self.wait_window(manager_window)
        self.load_skus()


# --- Run the Application ---
if __name__ == "__main__":
    app = Application()
    app.mainloop()
