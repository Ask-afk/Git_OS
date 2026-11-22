"""Export the public interface demo, excluding the authenticated server."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
output = root / "public-demo"
output.mkdir(exist_ok=True)
for name in ("index.html", "style.css", "brand.js", "app.js"):
    shutil.copy2(root / "ui" / name, output / name)
shutil.copytree(root / "ui/assets", output / "assets", dirs_exist_ok=True)
index = (output / "index.html").read_text()
index = index.replace(
    '<script defer src="app.js">',
    '<script defer src="demo.js"></script><script defer src="app.js">',
)
index = index.replace(
    '<body>',
    '<body><aside class="demo-banner">Public interface demo · Sample data · '
    'Password protection and local AI are available in the installed version. '
    '<a href="https://github.com/Ask-afk/Git_OS">Source and setup guide</a></aside>',
)
index = index.replace('aria-label="Lock Daywell">Lock', 'aria-label="Reset demo">Reset demo')
(output / "index.html").write_text(index)
(output / "demo.js").write_text("window.DAYWELL_PUBLIC_DEMO = true;\n")
with (output / "style.css").open("a") as css:
    css.write("\n.demo-banner{padding:16px 5vw;background:#23382e;color:#faf9f6;font:18px/1.5 system-ui}.demo-banner a{color:inherit;text-decoration:underline}\n")
(output / ".nojekyll").touch()
print(output)
