import os
from github import Github

pat = os.getenv("GITHUB_TOKEN")
g = Github(pat)

for repo in g.get_user().get_repos():
    print(repo.name)
