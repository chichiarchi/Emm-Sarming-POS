from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QLineEdit, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
import database

class AccountModule(QWidget):
    logout_requested = Signal()

    def __init__(self, username, user_role="staff"):
        super().__init__()
        self.username = username
        self.user_role = user_role
        self.setup_ui()

    def setup_ui(self):
        # Main layout for the module
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Header Section
        header_layout = QVBoxLayout()
        title = QLabel("Account Settings")
        title.setStyleSheet("""
            font-size: 28px; 
            font-weight: 800; 
            color: #064E3B; 
            letter-spacing: -0.5px;
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Manage your profile, security preferences, and users")
        subtitle.setStyleSheet("font-size: 14px; color: #4B5563; margin-top: -5px;")
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)

        # Content Layout
        content_wrapper = QHBoxLayout()
        content_container = QVBoxLayout()
        content_container.setSpacing(25)

        # Profile Card
        profile_card = QFrame()
        profile_card.setObjectName("card")
        profile_card.setStyleSheet("""
            QFrame#card {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        profile_layout = QVBoxLayout(profile_card)

        profile_title = QLabel("User Profile")
        profile_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #064E3B; margin-bottom: 10px;")
        profile_layout.addWidget(profile_title)

        user_info_layout = QHBoxLayout()
        user_icon = QLabel("👤")
        user_icon.setStyleSheet("font-size: 32px; background-color: #F3F4F6; border-radius: 20px; padding: 10px;")
        user_info_layout.addWidget(user_icon)
        
        user_details = QVBoxLayout()
        user_name_lbl = QLabel(self.username)
        user_name_lbl.setStyleSheet("font-size: 18px; font-weight: 600; color: #1F2937;")
        user_details.addWidget(user_name_lbl)
        
        role_lbl = QLabel(self.user_role.upper())
        role_lbl.setStyleSheet("font-size: 13px; color: #4B5563; text-transform: uppercase; letter-spacing: 1px;")
        user_details.addWidget(role_lbl)
        
        user_info_layout.addLayout(user_details)
        user_info_layout.addStretch()
        profile_layout.addLayout(user_info_layout)
        
        content_container.addWidget(profile_card)

        # Password Change Section
        pwd_container = QFrame()
        pwd_container.setObjectName("card")
        pwd_container.setStyleSheet("""
            QFrame#card {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 16px;
                padding: 24px;
            }
            QLabel {
                font-size: 14px;
                color: #4B5563;
                font-weight: 600;
                margin-bottom: 4px;
            }
            QLineEdit {
                background-color: #F9FAFB;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                margin-bottom: 16px;
            }
            QLineEdit:focus {
                border: 2px solid #064E3B;
                background-color: #FFFFFF;
            }
        """)
        pwd_layout = QVBoxLayout(pwd_container)
        
        pwd_title = QLabel("Security & Password")
        pwd_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #064E3B; margin-bottom: 15px;")
        pwd_layout.addWidget(pwd_title)

        pwd_layout.addWidget(QLabel("Current Password"))
        self.current_pwd = QLineEdit()
        self.current_pwd.setPlaceholderText("Enter current password")
        self.current_pwd.setEchoMode(QLineEdit.Password)
        pwd_layout.addWidget(self.current_pwd)

        pwd_layout.addWidget(QLabel("New Password"))
        self.new_pwd = QLineEdit()
        self.new_pwd.setPlaceholderText("Enter new password")
        self.new_pwd.setEchoMode(QLineEdit.Password)
        pwd_layout.addWidget(self.new_pwd)

        pwd_layout.addWidget(QLabel("Confirm New Password"))
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setPlaceholderText("Confirm new password")
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        pwd_layout.addWidget(self.confirm_pwd)

        self.btn_update_pwd = QPushButton("Update Password")
        self.btn_update_pwd.setCursor(Qt.PointingHandCursor)
        self.btn_update_pwd.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #064E3B, stop:1 #0D9488);
                color: white;
                font-size: 15px;
                font-weight: 700;
                padding: 14px;
                border: none;
                border-radius: 8px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #14B8A6);
            }
            QPushButton:pressed {
                padding-top: 15px;
                background-color: #064E3B;
            }
        """)
        self.btn_update_pwd.clicked.connect(self.update_password)
        pwd_layout.addWidget(self.btn_update_pwd)

        content_container.addWidget(pwd_container)

        # User Manager Card (Only visible to Admins)
        if self.user_role == "admin":
            user_card = QFrame()
            user_card.setObjectName("card")
            user_card.setStyleSheet("""
                QFrame#card {
                    background-color: #FFFFFF;
                    border: 1px solid #D1D5DB;
                    border-radius: 16px;
                    padding: 24px;
                }
            """)
            user_layout = QVBoxLayout(user_card)
            
            user_title = QLabel("User Management")
            user_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #064E3B; margin-bottom: 15px;")
            user_layout.addWidget(user_title)
            
            self.user_table = QTableWidget(0, 2)
            self.user_table.setHorizontalHeaderLabels(["Username", "Role"])
            self.user_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.user_table.setMinimumHeight(180)
            self.user_table.setStyleSheet("""
                QTableWidget {
                    background-color: #FFFFFF;
                    border: 1px solid #D1D5DB;
                    border-radius: 8px;
                    color: #1F2937;
                }
            """)
            user_layout.addWidget(self.user_table)
            
            btn_layout = QHBoxLayout()
            btn_add = QPushButton("Add New User")
            btn_add.clicked.connect(self.show_add_user_dialog)
            btn_add.setStyleSheet("""
                QPushButton {
                    background-color: #064E3B;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 10px 16px;
                    border: none;
                }
                QPushButton:hover { background-color: #047857; }
            """)
            
            btn_change_pwd = QPushButton("Edit Password")
            btn_change_pwd.clicked.connect(self.edit_selected_user_password)
            btn_change_pwd.setStyleSheet("""
                QPushButton {
                    background-color: #D97706;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 10px 16px;
                    border: none;
                }
                QPushButton:hover { background-color: #B45309; }
            """)

            btn_delete = QPushButton("Delete Selected")
            btn_delete.clicked.connect(self.delete_selected_user)
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #EF4444;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 10px 16px;
                    border: none;
                }
                QPushButton:hover { background-color: #DC2626; }
            """)
            
            btn_layout.addWidget(btn_add)
            btn_layout.addWidget(btn_change_pwd)
            btn_layout.addWidget(btn_delete)
            user_layout.addLayout(btn_layout)
            
            content_container.addWidget(user_card)
            self.load_users()

        # Logout Button Section
        logout_btn = QPushButton("Logout from System")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                font-size: 15px;
                font-weight: 700;
                padding: 14px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
            QPushButton:pressed {
                background-color: #B91C1C;
            }
        """)
        logout_btn.clicked.connect(self.logout_requested.emit)
        content_container.addWidget(logout_btn)
        
        # Add stretch to keep cards at the top
        content_container.addStretch()
        
        content_wrapper.addLayout(content_container)
        content_wrapper.addStretch() # Push everything to the left
        
        layout.addLayout(content_wrapper)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def update_password(self):
        current_pwd = self.current_pwd.text().strip()
        new_pwd = self.new_pwd.text().strip()
        confirm_pwd = self.confirm_pwd.text().strip()

        if not current_pwd or not new_pwd or not confirm_pwd:
            QMessageBox.warning(self, "Validation Error", "All password fields must be filled.")
            return

        if new_pwd != confirm_pwd:
            QMessageBox.warning(self, "Validation Error", "The new passwords do not match. Please try again.")
            return

        if len(new_pwd) < 6:
            QMessageBox.warning(self, "Validation Error", "The new password must be at least 6 characters long.")
            return

        # Verify current password
        user_data = database.verify_login(self.username, current_pwd)
        if not user_data:
            QMessageBox.critical(self, "Security Error", "The current password you entered is incorrect.")
            return

        # Update password
        if database.update_user_password(self.username, new_pwd):
            QMessageBox.information(self, "Success", "Your password has been updated successfully.")
            self.current_pwd.clear()
            self.new_pwd.clear()
            self.confirm_pwd.clear()
            database.log_action("PASSWORD_CHANGE", f"User '{self.username}' updated their password.", self.username)
        else:
            QMessageBox.critical(self, "System Error", "An error occurred while updating the password. Please try again later.")

    def load_users(self):
        if self.user_role != "admin":
            return
        users = database.get_all_users()
        self.user_table.setRowCount(0)
        for i, (uid, name, role) in enumerate(users):
            self.user_table.insertRow(i)
            self.user_table.setItem(i, 0, QTableWidgetItem(name))
            self.user_table.setItem(i, 1, QTableWidgetItem(role.capitalize()))

    def show_add_user_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add User")
        dialog.setMinimumWidth(320)
        
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        
        inp_uname = QLineEdit()
        inp_pwd = QLineEdit()
        inp_pwd.setEchoMode(QLineEdit.Password)
        
        inp_role = QComboBox()
        inp_role.addItems(["Admin", "Staff"])
        
        form.addRow("Username:", inp_uname)
        form.addRow("Password:", inp_pwd)
        form.addRow("Role:", inp_role)
        layout.addLayout(form)
        
        btn_save = QPushButton("Save User")
        btn_save.setStyleSheet("""
            background-color: #064E3B;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-radius: 6px;
            border: none;
        """)
        btn_save.clicked.connect(dialog.accept)
        layout.addWidget(btn_save)
        
        if dialog.exec():
            uname = inp_uname.text().strip()
            pwd = inp_pwd.text().strip()
            role = inp_role.currentText().lower()
            
            if not uname or not pwd:
                QMessageBox.warning(self, "Error", "Username and Password cannot be empty.")
                return
                
            if database.create_user(uname, pwd, role):
                QMessageBox.information(self, "Success", f"User '{uname}' added successfully.")
                database.log_action("USER_ADDED", f"Added user '{uname}' with role '{role}'", self.username)
                self.load_users()
            else:
                QMessageBox.critical(self, "Error", "Username already exists or failed to add user.")

    def delete_selected_user(self):
        current_row = self.user_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a user to delete.")
            return
            
        username = self.user_table.item(current_row, 0).text()
        
        if username == self.username:
            QMessageBox.warning(self, "Action Denied", "You cannot delete your own logged-in account.")
            return
            
        if username == 'admin':
            QMessageBox.warning(self, "Action Denied", "The default 'admin' user cannot be deleted.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete", f"Are you sure you want to completely delete user '{username}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if database.delete_user(username):
                QMessageBox.information(self, "Success", f"User '{username}' deleted successfully.")
                database.log_action("USER_DELETED", f"Deleted user '{username}'", self.username)
                self.load_users()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete user.")

    def edit_selected_user_password(self):
        current_row = self.user_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a user first.")
            return
            
        username = self.user_table.item(current_row, 0).text()
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Change Password for {username}")
        dialog.setMinimumWidth(320)
        
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        
        inp_pwd = QLineEdit()
        inp_pwd.setEchoMode(QLineEdit.Password)
        inp_confirm = QLineEdit()
        inp_confirm.setEchoMode(QLineEdit.Password)
        
        form.addRow("New Password:", inp_pwd)
        form.addRow("Confirm Password:", inp_confirm)
        layout.addLayout(form)
        
        btn_save = QPushButton("Save Password")
        btn_save.setStyleSheet("""
            background-color: #064E3B;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-radius: 6px;
            border: none;
        """)
        btn_save.clicked.connect(dialog.accept)
        layout.addWidget(btn_save)
        
        if dialog.exec():
            pwd = inp_pwd.text().strip()
            confirm = inp_confirm.text().strip()
            
            if not pwd:
                QMessageBox.warning(self, "Error", "Password cannot be empty.")
                return
                
            if pwd != confirm:
                QMessageBox.warning(self, "Error", "Passwords do not match.")
                return
                
            if len(pwd) < 6:
                QMessageBox.warning(self, "Error", "Password must be at least 6 characters long.")
                return
                
            if database.update_user_password(username, pwd):
                QMessageBox.information(self, "Success", f"Password for '{username}' updated successfully.")
                database.log_action("USER_PASSWORD_CHANGE_BY_ADMIN", f"Admin updated password for user '{username}'", self.username)
            else:
                QMessageBox.critical(self, "Error", "Failed to update password.")
