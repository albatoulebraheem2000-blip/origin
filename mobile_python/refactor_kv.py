import re

with open("origin.kv", "r", encoding="utf-8") as f:
    content = f.read()

old_manager = """<MainManager>:
    canvas.before:
        Color:
            rgba: (.965, .975, .99, 1)
        Rectangle:
            pos: self.pos
            size: self.size"""

new_manager = """<MainManager>:
    orientation: "horizontal" if app.is_desktop else "vertical"
    canvas.before:
        Color:
            rgba: (.965, .975, .99, 1)
        Rectangle:
            pos: self.pos
            size: self.size
            
    BoxLayout:
        orientation: "vertical"
        size_hint_x: None
        width: dp(220) if app.is_desktop and app.user else 0
        opacity: 1 if app.is_desktop and app.user else 0
        disabled: not (app.is_desktop and app.user)
        padding: dp(16)
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: (1, 1, 1, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Origin AI"
            color: (0.05, 0.12, 0.25, 1)
            font_size: "24sp"
            bold: True
            size_hint_y: None
            height: dp(60)
        Button:
            text: "الرئيسية / Home"
            size_hint_y: None
            height: dp(50)
            on_release: sm.current = "home"
        Button:
            text: "الأصول / Assets"
            size_hint_y: None
            height: dp(50)
            on_release: sm.current = "assets"
        Button:
            text: "النقل / Transfers"
            size_hint_y: None
            height: dp(50)
            on_release: sm.current = "transfers"
        Button:
            text: "السوق / Market"
            size_hint_y: None
            height: dp(50)
            on_release: sm.current = "market"
        Button:
            text: "الحساب / Profile"
            size_hint_y: None
            height: dp(50)
            on_release: sm.current = "profile"
        Widget:

    BoxLayout:
        orientation: "vertical"
        ScreenManager:
            id: sm
            
        BoxLayout:
            size_hint_y: None
            height: dp(58) if (not app.is_desktop and app.user and sm.current in ["home", "assets", "transfers", "market", "profile"]) else 0
            opacity: 1 if self.height > 0 else 0
            disabled: self.height == 0
            spacing: dp(4)
            canvas.before:
                Color:
                    rgba: (1, 1, 1, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: "الرئيسية\\nHome"
                on_release: sm.current = "home"
            Button:
                text: "الأصول\\nAssets"
                on_release: sm.current = "assets"
            Button:
                text: "النقل\\nTransfers"
                on_release: sm.current = "transfers"
            Button:
                text: "السوق\\nMarket"
                on_release: sm.current = "market"
            Button:
                text: "الحساب\\nProfile"
                on_release: sm.current = "profile"
"""

content = content.replace(old_manager, new_manager)

# We want to remove the specific navigation BoxLayouts.
# They are exactly the ones starting with:
#         BoxLayout:
#             size_hint_y: None
#             height: dp(58)
#             spacing: dp(4)
# and ending before a line with indentation less than or equal to 8 spaces, or end of string.

pattern = r'        BoxLayout:\n            size_hint_y: None\n            height: dp\(58\)\n            spacing: dp\(4\)\n(?:            Button:\n(?:                .*?\n)+)+?(?=^\S|^ {0,7}\S|\Z)'
content = re.sub(pattern, '', content, flags=re.MULTILINE)

# Also fix the desktop width for Field and PrimaryButton
content = content.replace("<PrimaryButton@Button>:\n    size_hint_y: None", "<PrimaryButton@Button>:\n    size_hint_y: None\n    size_hint_x: None if app.is_desktop else 1\n    width: dp(400) if app.is_desktop else self.parent.width\n    pos_hint: {'center_x': 0.5}")
content = content.replace("<Field@TextInput>:\n    size_hint_y: None", "<Field@TextInput>:\n    size_hint_y: None\n    size_hint_x: None if app.is_desktop else 1\n    width: dp(400) if app.is_desktop else self.parent.width\n    pos_hint: {'center_x': 0.5}")

with open("origin.kv", "w", encoding="utf-8") as f:
    f.write(content)
print("done")
