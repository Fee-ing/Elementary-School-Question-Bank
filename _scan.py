import urllib.request, json, time, re

def get(url):
    req = urllib.request.Request(url, headers={'Accept':'application/vnd.github+json','User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

# cloned set (skip)
cloned = {
 "mengxiaoyucc/MidAnswer","thl529/question-bank","onepolar1/MyMathLib","h517061544/test",
 "superorcz/math-question-bank","r4c4gzpzyh-gif/six-science-quiz-second-20260530-build-by-sherry-su",
 "lingchunya/practice-sheet","cbicbicn/xxs","cbicbicn/xxsjs","Kevin-Yong/primary-question-bank",
 "holidaysss/Calculator","CC-1368/primary-school-math-bank","cuigu/math-resource-library"
}
data_ext = re.compile(r'\.(json|jsonl|csv|tsv|txt|xlsx?|pdf|dat|md|js)$', re.I)

repos=[]
for page in (1,2):
    url=f"https://api.github.com/search/repositories?q=%E5%B0%8F%E5%AD%A6+%E9%A2%98%E5%BA%93&sort=stars&order=desc&per_page=30&page={page}"
    d=get(url)
    for it in d['items']:
        repos.append((it['full_name'], it.get('default_branch','main'), it['stargazers_count']))

print(f"total repos: {len(repos)}")
results=[]
for full, branch, stars in repos:
    if full in cloned:
        continue
    try:
        trees=get(f"https://api.github.com/repos/{full}/git/trees/{branch}?recursive=1")
        files=[t['path'] for t in trees.get('tree',[]) if t.get('type')=='blob']
        data=[f for f in files if data_ext.search(f) and not f.lower().endswith(('min.js','echarts.min.js','mermaid.min.js'))]
        # further filter: focus on likely question data (exclude node_modules, lock, configs)
        interesting=[f for f in data if re.search(r'(题|tiku|question|quiz|bank|题库|exercise|exam|answer)', f, re.I) or f.lower().endswith(('.json','.jsonl','.csv','.xlsx','.pdf'))]
        results.append((full, stars, len(files), interesting))
    except Exception as e:
        results.append((full, stars, -1, [f'ERR:{e}']))
    time.sleep(0.15)

with open('_scan_results.json','w') as f:
    json.dump([(r[0],r[1],r[2],r[3]) for r in results], f, ensure_ascii=False, indent=1)

for full, stars, n, df in results:
    flag = "DATA" if df else "----"
    print(f"[{flag}] {full} (stars={stars}, files={n})")
    for f in df[:15]:
        print("     ", f)
