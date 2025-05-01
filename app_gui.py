# File: app_gui.py
import tkinter as tk
from tkinter import ttk
from tkinter import (
    scrolledtext,
    messagebox,
    Frame,
    Scrollbar,
    END,
    Button,
    Label,
    Entry,
    Scale,
    IntVar,
    StringVar,
    Radiobutton,
    LabelFrame,
)
import database as db
import matching  # Import the matching logic module
import constants  # Import constants
from sku_manager_gui import SkuManagerWindow  # Import the SKU manager window
import os
import sys


class Application(tk.Tk):
    """Main application class."""

    def __init__(self):
        super().__init__()
        self.title("Product Name to SKU Converter")
        self.geometry("700x720")

        # --- Determine Base Path ---
        if getattr(sys, "frozen", False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
        print(f"Application base path: {self.base_path}")

        # --- Variables ---
        self.all_skus = []
        self._warned_no_skus = False
        self.similarity_threshold = IntVar(value=constants.DEFAULT_THRESHOLD)
        self.engine_choice = StringVar(value=constants.ENGINE_FUZZY)
        self.api_key_var = StringVar()  # Holds GUI entry text for API key
        self.selected_gemini_model = StringVar(value=constants.DEFAULT_GEMINI_MODEL)

        # --- Read potential API Key sources (ENV and File) ---
        self.env_api_key = os.environ.get(constants.GEMINI_API_ENV_VAR)
        self.file_api_key = None
        key_file_path = os.path.join(self.base_path, constants.API_KEY_FILENAME)
        try:
            with open(key_file_path, "r", encoding="utf-8") as f:
                key_from_file = f.readline().strip()
                if key_from_file:
                    self.file_api_key = key_from_file
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading API key file '{key_file_path}': {e}")
        if self.env_api_key:
            print(f"Info: Found Gemini API key in ENV var.")
        if self.file_api_key:
            print(f"Info: Read API key from {constants.API_KEY_FILENAME}.")

        # --- Widgets ---
        self._setup_widgets()

        # --- Initialization ---
        self.load_skus()
        self.toggle_controls()  # Set initial UI state

    def _setup_widgets(self):
        """Creates and lays out all the GUI widgets."""
        # Input Frame (Left)
        input_frame = Frame(self)
        input_label = Label(input_frame, text="Paste Product Names (one per line):")
        self.input_text = scrolledtext.ScrolledText(
            input_frame, height=15, width=40, wrap=tk.WORD
        )

        # --- Control Frame (Center) ---
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
            value=constants.ENGINE_FUZZY,
            command=self.toggle_controls,
        )
        gemini_radio_state = tk.NORMAL if matching.GEMINI_AVAILABLE else tk.DISABLED
        self.gemini_radio = Radiobutton(
            engine_frame,
            text="Gemini AI",
            variable=self.engine_choice,
            value=constants.ENGINE_GEMINI,
            command=self.toggle_controls,
            state=gemini_radio_state,
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

        # -- Gemini Controls Frame --
        self.gemini_controls_frame = Frame(control_frame)

        # API Key Sub-Frame
        api_key_subframe = Frame(self.gemini_controls_frame)
        api_key_label = Label(api_key_subframe, text="Gemini API Key:")
        self.api_key_entry = Entry(
            api_key_subframe, textvariable=self.api_key_var, width=20, show="*"
        )
        self.api_key_info_label = Label(
            api_key_subframe,
            text=f"(Priority: Entry > {constants.API_KEY_FILENAME} > ENV)",
            fg="blue",
            cursor="hand2",
        )
        self.api_key_info_label.bind(
            "<Button-1>",
            lambda e: messagebox.showinfo(
                "API Key Info",
                f"API Key Loading Priority:\n1. Manual entry here.\n2. File: {constants.API_KEY_FILENAME}\n3. Env Var: {constants.GEMINI_API_ENV_VAR}\n\nThe first non-empty key found is used.",
                parent=self,
            ),
        )

        # Model Selection Sub-Frame
        model_select_subframe = Frame(self.gemini_controls_frame)
        model_label = Label(model_select_subframe, text="Gemini Model:")
        if not constants.AVAILABLE_GEMINI_MODELS:
            self.model_combobox = Label(
                model_select_subframe, text="No models defined", fg="red"
            )
        else:
            self.model_combobox = ttk.Combobox(
                model_select_subframe,
                textvariable=self.selected_gemini_model,
                values=constants.AVAILABLE_GEMINI_MODELS,
                state="readonly",
                width=18,
            )
            if constants.DEFAULT_GEMINI_MODEL not in constants.AVAILABLE_GEMINI_MODELS:
                self.selected_gemini_model.set(constants.AVAILABLE_GEMINI_MODELS[0])

        # Prompt Instruction Sub-Frame
        prompt_instr_subframe = Frame(self.gemini_controls_frame)
        instr_label = Label(prompt_instr_subframe, text="Gemini Prompt Instructions:")
        self.prompt_instr_text = scrolledtext.ScrolledText(
            prompt_instr_subframe, height=6, width=30, wrap=tk.WORD
        )
        # Load saved instructions or use default
        saved_instructions = db.load_setting(constants.DB_SETTING_GEMINI_INSTRUCTIONS)
        initial_instructions = (
            saved_instructions
            if saved_instructions
            else constants.DEFAULT_GEMINI_INSTRUCTIONS
        )
        self.prompt_instr_text.insert("1.0", initial_instructions)

        # Add button to load default instructions
        self.load_default_prompt_button = Button(
            prompt_instr_subframe,
            text="Load Default",
            command=self.load_default_instructions,
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
        self.convert_button.pack(pady=(10, 15))
        self.manage_button.pack(pady=15)
        engine_frame.pack(pady=(15, 10), padx=5, fill=tk.X)
        self.fuzzy_radio.pack(anchor=tk.W)
        self.gemini_radio.pack(anchor=tk.W)

        # Pack Fuzzy frame (managed by toggle_controls)
        self.threshold_frame.pack(pady=5, padx=5, fill=tk.X)
        threshold_label.pack(side=tk.LEFT)
        self.threshold_value_label.pack(side=tk.LEFT, padx=2)
        self.threshold_scale.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Pack Gemini frame (managed by toggle_controls)
        self.gemini_controls_frame.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
        # Layout Gemini sub-frames
        api_key_subframe.pack(pady=(5, 0), fill=tk.X)
        api_key_label.pack(anchor=tk.W)
        self.api_key_entry.pack(fill=tk.X, pady=(0, 2))
        self.api_key_info_label.pack(anchor=tk.W)

        model_select_subframe.pack(pady=(5, 0), fill=tk.X)
        model_label.pack(anchor=tk.W)
        self.model_combobox.pack(fill=tk.X)

        prompt_instr_subframe.pack(pady=5, fill=tk.BOTH, expand=True)
        instr_label.pack(anchor=tk.W)
        self.prompt_instr_text.pack(
            fill=tk.BOTH, expand=True, pady=(0, 5)
        )  # Add padding below
        self.load_default_prompt_button.pack(anchor=tk.E)  # Pack button below text area

        output_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        output_label.pack(anchor=tk.W, pady=(0, 5))
        self.output_text.pack(fill=tk.BOTH, expand=True)

    def toggle_controls(self):
        """Show/hide controls based on selected engine."""
        selected_engine = self.engine_choice.get()
        if selected_engine == constants.ENGINE_FUZZY:
            self.threshold_frame.pack(pady=5, padx=5, fill=tk.X)
            self.gemini_controls_frame.pack_forget()
        elif selected_engine == constants.ENGINE_GEMINI and matching.GEMINI_AVAILABLE:
            self.threshold_frame.pack_forget()
            self.gemini_controls_frame.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
            self.api_key_entry.config(state=tk.NORMAL)
            if self.api_key_var.get().startswith(
                "Detected in"
            ):  # Clear placeholder if user switches
                self.api_key_var.set("")
        else:
            self.threshold_frame.pack_forget()
            self.gemini_controls_frame.pack_forget()
            if (
                selected_engine == constants.ENGINE_GEMINI
                and not matching.GEMINI_AVAILABLE
            ):
                messagebox.showerror(
                    "Missing Library", "Gemini AI library not installed.", parent=self
                )

    def load_default_instructions(self):
        """Loads the default Gemini prompt instructions into the text box."""
        self.prompt_instr_text.delete("1.0", tk.END)
        self.prompt_instr_text.insert("1.0", constants.DEFAULT_GEMINI_INSTRUCTIONS)
        messagebox.showinfo(
            "Prompt Loaded", "Default Gemini prompt instructions loaded.", parent=self
        )

    def load_skus(self):
        """Loads/reloads the list of SKUs from the database into memory."""
        self.all_skus = db.get_all_skus()
        print(f"Loaded {len(self.all_skus)} SKUs into memory.")
        if not self.all_skus and not self._warned_no_skus:
            messagebox.showwarning(
                "No SKUs Loaded",
                "SKU database is empty. Use 'Manage SKUs'.",
                parent=self,
            )
            self._warned_no_skus = True

    def perform_conversion(self):
        """Reads input, finds matches using the selected engine, and displays results."""
        selected_engine = self.engine_choice.get()
        print(f"Starting conversion using engine: {selected_engine}")

        if selected_engine == constants.ENGINE_GEMINI and not matching.GEMINI_AVAILABLE:
            messagebox.showerror(
                "Missing Library",
                "Cannot use Gemini: 'google-generativeai' library not installed.",
            )
            return

        input_content = self.input_text.get("1.0", tk.END).strip()
        if not input_content:
            messagebox.showwarning(
                "Input Error", "Paste product names into the input area.", parent=self
            )
            return
        product_names = [
            name.strip() for name in input_content.splitlines() if name.strip()
        ]
        if not product_names:
            messagebox.showwarning(
                "Input Error", "No valid product names found in input.", parent=self
            )
            return
        self.load_skus()
        if not self.all_skus:
            messagebox.showerror(
                "Error", "No SKUs available in the database.", parent=self
            )
            return

        matched_skus = []
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(
            tk.END, f"Processing {len(product_names)} items using {selected_engine}..."
        )
        if selected_engine == constants.ENGINE_GEMINI:
            self.output_text.insert(tk.END, "\n(This may take a while...)")
        self.output_text.config(state=tk.DISABLED)
        self.update_idletasks()

        # --- Engine-Specific Logic ---
        if selected_engine == constants.ENGINE_FUZZY:
            current_threshold = self.similarity_threshold.get()
            matched_skus = [
                matching.find_best_sku_match_fuzzy(
                    name, self.all_skus, current_threshold
                )
                for name in product_names
            ]

        elif selected_engine == constants.ENGINE_GEMINI:
            # Determine API Key
            api_key_to_use = None
            source = "Not Found"
            gui_key = self.api_key_var.get().strip()
            if gui_key:
                api_key_to_use = gui_key
                source = "GUI Entry"
            elif self.file_api_key:
                api_key_to_use = self.file_api_key
                source = f"{constants.API_KEY_FILENAME}"
            elif self.env_api_key:
                api_key_to_use = self.env_api_key
                source = "Environment Variable"

            # Get Model and Instructions
            selected_model = self.selected_gemini_model.get()
            custom_instructions = self.prompt_instr_text.get("1.0", tk.END).strip()

            # Validate Inputs
            if not api_key_to_use:
                messagebox.showerror(
                    "API Key Error", "Gemini API Key not found.", parent=self
                )
                self._show_error_in_output("Cancelled: Missing API Key")
                return
            if not selected_model:
                messagebox.showerror(
                    "Model Error", "No Gemini model selected.", parent=self
                )
                self._show_error_in_output("Cancelled: No Model Selected")
                return
            if not custom_instructions:
                messagebox.showerror(
                    "Instructions Error",
                    "Gemini prompt instructions empty.",
                    parent=self,
                )
                self._show_error_in_output("Cancelled: Missing Instructions")
                return

            # Save the used instructions for next time
            db.save_setting(
                constants.DB_SETTING_GEMINI_INSTRUCTIONS, custom_instructions
            )

            # Process Items
            print(f"Using API key from: {source}. Model: {selected_model}.")
            for i, name in enumerate(product_names):
                match_result = matching.find_best_sku_match_gemini(
                    name,
                    self.all_skus,
                    api_key_to_use,
                    selected_model,
                    custom_instructions,
                )
                matched_skus.append(match_result)
                if "ERROR:" in match_result and "ERROR DURING" not in match_result:
                    error_msg = f"API Error: {match_result}"
                    if "INVALID API KEY" in match_result:
                        error_msg = f"Invalid API Key (from {source}). Check key."
                    elif (
                        "MODEL" in match_result
                        and "NOT FOUND/ACCESSIBLE" in match_result
                    ):
                        error_msg = f"Model '{selected_model}' not found/accessible."
                    elif "MISSING API KEY" in match_result:
                        error_msg = (
                            "Gemini API Key missing."  # Should be caught earlier
                        )
                    messagebox.showerror("Gemini Error", error_msg, parent=self)
                    break  # Stop processing

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

    def _show_error_in_output(self, message):
        """Helper to display cancellation/error messages in the output box."""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, message)
        self.output_text.config(state=tk.DISABLED)

    def open_sku_manager(self):
        """Opens the SKU Management window."""
        manager = SkuManagerWindow(self)  # Use imported class
        self.wait_window(manager)
        self.load_skus()  # Reload SKUs after manager closes
