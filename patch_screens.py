import sys

file_path = r"c:\Users\javiru\Desktop\viru-tracker\frontend\src\styles\screens.css"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
except FileNotFoundError:
    print(f"Error: Could not find {file_path}")
    sys.exit(1)

block1_find = """\
.qs-filters-panel.open {
  transform: translateX(0);
}

.qs-filters-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  border: none;
  background: rgba(18, 24, 30, 0.42);
  touch-action: none;
}"""

block1_replace = """\
@keyframes qs-drawer-slide-in {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

@keyframes qs-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.qs-filters-panel.open {
  transform: translateX(0);
  animation: qs-drawer-slide-in 0.35s cubic-bezier(0.2, 0, 0, 1) forwards;
}

.qs-filters-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  border: none;
  background: color-mix(in srgb, var(--ink) 42%, transparent);
  touch-action: none;
  animation: qs-fade-in 0.3s ease forwards;
}"""

block2_find = """\
.qs-filter-console-card,
.qs-filter-preset {
  display: grid;
  gap: 0.28rem;
  min-width: 0;
  border: 1px solid color-mix(in srgb, var(--border) 76%, white 24%);
  border-radius: 16px;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--surface) 92%, white 8%), color-mix(in srgb, var(--surface-2) 42%, var(--surface) 58%));
  color: var(--ink);
  text-align: left;
  padding: 0.78rem 0.82rem;
  cursor: pointer;
  box-shadow:
    0 6px 14px rgba(32, 28, 21, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.56);
}

.qs-filter-console-card:hover,
.qs-filter-console-card:focus-visible,
.qs-filter-preset:hover,
.qs-filter-preset:focus-visible {
  border-color: color-mix(in srgb, var(--accent) 34%, var(--border));
  outline: none;
  transform: translateY(-1px);
}"""

block2_replace = """\
.qs-filter-console-card,
.qs-filter-preset {
  display: grid;
  gap: 0.28rem;
  min-width: 0;
  border: 1px solid color-mix(in srgb, var(--border) 76%, white 24%);
  border-radius: 16px;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--surface) 92%, white 8%), color-mix(in srgb, var(--surface-2) 42%, var(--surface) 58%));
  color: var(--ink);
  text-align: left;
  padding: 0.78rem 0.82rem;
  cursor: pointer;
  box-shadow:
    0 6px 14px rgba(32, 28, 21, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.56);
  transition: transform 0.2s cubic-bezier(0.2, 0, 0, 1), box-shadow 0.2s cubic-bezier(0.2, 0, 0, 1), border-color 0.2s ease;
}

.qs-filter-console-card:hover,
.qs-filter-console-card:focus-visible,
.qs-filter-preset:hover,
.qs-filter-preset:focus-visible {
  border-color: color-mix(in srgb, var(--accent) 34%, var(--border));
  outline: none;
  transform: translateY(-2px);
  box-shadow:
    0 12px 24px rgba(47, 40, 24, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

.qs-filter-console-card:active,
.qs-filter-preset:active {
  transform: translateY(0) scale(0.98);
  box-shadow:
    0 4px 10px rgba(47, 40, 24, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
}"""

block3_find = """\
.qs-filter-count,
.qs-filter-support {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--border) 74%, white 26%);
  background: color-mix(in srgb, var(--surface) 86%, white 14%);
  color: var(--ink);
  padding: 0.34rem 0.62rem;
  font-size: 0.76rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}"""

block3_replace = """\
.qs-filter-count,
.qs-filter-support {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--border) 74%, white 26%);
  background: color-mix(in srgb, var(--surface) 86%, white 14%);
  color: var(--ink);
  padding: 0.34rem 0.62rem;
  font-size: 0.76rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}"""

block4_find = """\
.qs-filter-console-drawer .qs-input,
.qs-filter-console-drawer select.qs-input,
.qs-filter-console-drawer input.qs-input {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: 0.62rem 0.78rem;
}"""

block4_replace = """\
.qs-filter-console-drawer .qs-input,
.qs-filter-console-drawer select.qs-input,
.qs-filter-console-drawer input.qs-input {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: 0.62rem 0.78rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}"""

blocks = [
    (block1_find, block1_replace),
    (block2_find, block2_replace),
    (block3_find, block3_replace),
    (block4_find, block4_replace),
]

for i, (f, r) in enumerate(blocks):
    # Try exact match
    new_content = content.replace(f, r)
    if new_content == content:
        # Try replacing line endings
        new_content = content.replace(f.replace("\\n", "\\r\\n"), r.replace("\\n", "\\r\\n"))
    
    # Try more robust replacement ignoring exact line endings
    if new_content == content:
        # Convert all content to \n for replacement
        normalized_content = content.replace("\\r\\n", "\\n")
        new_content = normalized_content.replace(f, r)
        # Restore original line endings (assuming the file was mostly \n or \r\n)
        if "\\r\\n" in content:
            new_content = new_content.replace("\\n", "\\r\\n")
            
    if new_content == content:
        print(f"Warning: Could not find block {i+1}")
    else:
        print(f"Replaced block {i+1}")
        content = new_content

with open(file_path, "w", encoding="utf-8", newline="") as f:
    f.write(content)
print("Done")
