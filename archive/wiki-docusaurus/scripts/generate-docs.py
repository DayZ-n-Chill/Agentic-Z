import os
import shutil
import re
import yaml

def sanitize_mdx(content, is_agent=False, is_skill=False):
    metadata = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try: metadata = yaml.safe_load(parts[1])
            except: pass
            frontmatter_raw = parts[1]
            body = parts[2]
            desc_match = re.search(r'description:\s*"(.*?)"(?=\n\w+:|\n$)', frontmatter_raw, re.DOTALL)
            if desc_match:
                description = desc_match.group(1)
                description = description.replace('\\n', '\n').replace('\\"', '"')
                new_frontmatter = re.sub(r'description:\s*".*?"(?=\n\w+:|\n$)', '', frontmatter_raw, flags=re.DOTALL)
                badges = "\n"
                if is_agent:
                    model = metadata.get('model', 'N/A')
                    color = metadata.get('color', 'grey')
                    badges += f'<span className="badge badge--primary" style="margin-right: 8px">Agent</span>'
                    badges += f'<span className="badge badge--secondary" style="margin-right: 8px">{model}</span>'
                    badges += f'<span className="badge" style="background-color: {color}; color: white">{color.capitalize()}</span>'
                elif is_skill:
                    badges += f'<span className="badge badge--info">Skill</span>'
                body = f"\n{badges}\n\n## Overview\n\n{description}\n\n" + body
                content = f'---{new_frontmatter}---{body}'

    content = re.sub(r'<(https?://[^>]+)>', r'[\1](\1)', content)
    content = re.sub(r'<(/?)([a-zA-Z0-9\-_]+)([^>]*)>', r'&lt;\1\2\3&gt;', content)
    content = re.sub(r'<(?!https?://)(?![ \t\n])', r'&lt;', content)
    return content

def fix_links(content, current_depth=0):
    prefix = '../' * current_depth
    if not prefix: prefix = './'
    
    # DayZ Conventions
    content = re.sub(r'\[([^\]]+)\]\([^)]*?dayz-conventions\.md\)', f'[\\1]({prefix}dayz-conventions)', content)
    content = re.sub(r'\[([^\]]+)\]\([^)]*?_shared\)', f'[\\1]({prefix}dayz-conventions)', content)
    
    # Skills
    def skill_match(m):
        text, full_path = m.group(1), m.group(2)
        sm = re.search(r'skills/([^/)]+)', full_path)
        if sm:
            skill = sm.group(1)
            if skill == '_shared': return f'[{text}]({prefix}dayz-conventions)'
            if current_depth == 0: return f'[{text}](./skills/{skill})'
            return f'[{text}](./{skill})'
        return m.group(0)
    content = re.sub(r'\[([^\]]+)\]\(([^)]*?\.claude/skills/[^)]+)\)', skill_match, content)
    
    # Agents
    def agent_match(m):
        text, full_path = m.group(1), m.group(2)
        am = re.search(r'agents/([^/)]+)', full_path)
        if am:
            agent = am.group(1).replace('.md', '')
            if current_depth == 0: return f'[{text}](./agents/{agent})'
            return f'[{text}](../agents/{agent})'
        return m.group(0)
    content = re.sub(r'\[([^\]]+)\]\(([^)]*?\.claude/agents/[^)]+)\)', agent_match, content)

    # MCP Links - Point to a generic placeholder or keep as text if not in wiki
    content = re.sub(r'\[([^\]]+)\]\([^)]*?\.claude/mcp/[^)]+\)', r'\1', content)

    if current_depth == 1:
        content = content.replace('](dayz-modding.md)', '](../dayz-modding)')
        content = content.replace('](intro.md)', '](../intro)')
    else:
        content = content.replace('](dayz-modding.md)', '](./dayz-modding)')
        content = content.replace('](intro.md)', '](./intro)')

    return content

def generate_docs():
    agents_src, skills_src = '.claude/agents', '.claude/skills'
    agents_dest, skills_dest = 'wiki/docs/agents', 'wiki/docs/skills'
    os.makedirs(agents_dest, exist_ok=True)
    os.makedirs(skills_dest, exist_ok=True)

    for src_name, dest_name in [('README.md', 'intro.md'), ('dayz-modding.md', 'dayz-modding.md')]:
        src_path = os.path.join('docs', src_name)
        dest_path = os.path.join('wiki/docs', dest_name)
        if os.path.exists(src_path):
            with open(src_path, 'r', encoding='utf-8') as f: content = f.read()
            content = sanitize_mdx(content)
            content = fix_links(content, current_depth=0)
            with open(dest_path, 'w', encoding='utf-8') as f: f.write(content)

    conventions_src = '.claude/skills/_shared/dayz-conventions.md'
    if os.path.exists(conventions_src):
        with open(conventions_src, 'r', encoding='utf-8') as f: content = f.read()
        content = sanitize_mdx(content)
        content = fix_links(content, current_depth=0)
        with open('wiki/docs/dayz-conventions.md', 'w', encoding='utf-8') as f: f.write(content)

    print("Generating Agents docs...")
    for f in [f for f in os.listdir(agents_src) if f.endswith('.md')]:
        src_path, dest_path = os.path.join(agents_src, f), os.path.join(agents_dest, f)
        with open(src_path, 'r', encoding='utf-8') as src: content = src.read()
        content = sanitize_mdx(content, is_agent=True)
        content = fix_links(content, current_depth=1)
        with open(dest_path, 'w', encoding='utf-8') as dest: dest.write(content)
        print(f"  Processed {f}")

    print("Generating Skills docs...")
    for skill_name in os.listdir(skills_src):
        skill_dir = os.path.join(skills_src, skill_name)
        if os.path.isdir(skill_dir) and not skill_name.startswith('_'):
            skill_md = os.path.join(skill_dir, 'SKILL.md')
            if os.path.exists(skill_md):
                dest_path = os.path.join(skills_dest, f"{skill_name}.md")
                with open(skill_md, 'r', encoding='utf-8') as src: content = src.read()
                content = sanitize_mdx(content, is_skill=True)
                content = fix_links(content, current_depth=1)
                with open(dest_path, 'w', encoding='utf-8') as dest: dest.write(content)
                print(f"  Processed {skill_name}/SKILL.md")

    with open(os.path.join(agents_dest, '_category_.json'), 'w', encoding='utf-8') as f:
        f.write('{\n  "label": "AI Agents",\n  "position": 3\n}')
    with open(os.path.join(skills_dest, '_category_.json'), 'w', encoding='utf-8') as f:
        f.write('{\n  "label": "Skills & Tools",\n  "position": 4\n}')

if __name__ == "__main__":
    generate_docs()
