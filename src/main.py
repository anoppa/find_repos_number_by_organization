from pathlib import Path
import json
import pandas as pd
from tqdm import tqdm
import numpy as np
import time
from pprint import pprint


def load_data(file):
    with file.open() as f:
        data = pd.read_csv(f)

    return data


def count_projects_ai_non_ai(organizations, data: pd.DataFrame):
    for row_index in tqdm(range(len(data))):
        row = data.iloc[row_index]
        full_name = row.get("full_name")
        org = full_name.split("/")[0]
        if org not in organizations:
            organizations[org] = {
                "count": 0,
                "ai_count": {"count": 0, "frameworks": []},
                "non_ai_count": 0,
            }
        frameworks = row.get("frameworks")
        if isinstance(frameworks, str):
            organizations[org]["count"] += 1
            frmks = frameworks.replace("[", "").replace("]", "").replace("'", "")
            if frmks == "":
                organizations[org]["non_ai_count"] += 1
            else:
                frmks = frmks.split(", ")
                organizations[org]["ai_count"]["count"] += 1
                organizations[org]["ai_count"]["frameworks"] = list(
                    set(organizations[org]["ai_count"]["frameworks"] + frmks)
                )


def projects_table(data, lang):
    rows = []
    for row_index in tqdm(range(len(data))):
        row = data.iloc[row_index]
        if row.get("error") != "":
            continue
        full_name = row.get("full_name").split("/")
        name = full_name[-1]
        org = full_name[0]
        url = row.get("url")
        frameworks = row.get("frameworks")
        libs = []
        if isinstance(frameworks, str):
            temp = frameworks.replace("[", "").replace("]", "").replace("'", "")
            if len(temp):
                libs = temp.split(", ")
        rows.append([name, org, url, lang, libs, 1, 1 if len(libs) else 0])
    return rows


def main():
    path = Path("data")
    rows = []
    for file in path.iterdir():
        if file.suffix == ".csv" and file.stem.startswith("output"):
            data = load_data(file)
            rows += projects_table(data, file.stem.split("_")[-1])
    table = pd.DataFrame(
        rows,
        columns=[
            "Name",
            "Organization",
            "Url",
            "Language",
            "AI-libraries",
            "Count",
            "AI_count",
        ],
    )
    grouped_by_organization = table.groupby(by=["Organization"]).sum()
    organizations_temp = []
    for r in grouped_by_organization.index:
        row = grouped_by_organization.loc[r]
        count = row.get("Count")
        ai_count = row.get("AI_count")
        if count > 100 and ai_count:
            organizations_temp.append((r, ai_count))
    top_5 = sorted(organizations_temp, key=lambda x: -x[1])[:5]
    top_5 = [s[0] for s in top_5]
    filter = (
        (table["Organization"] == top_5[0])
        | (table["Organization"] == top_5[1])
        | (table["Organization"] == top_5[2])
        | (table["Organization"] == top_5[3])
        | (table["Organization"] == top_5[4])
    )
    filter_orgs = (
        table.where(filter)
        .dropna(axis=0)
        .filter(items=["Name", "Organization", "Url", "Language", "AI-libraries"])
        .reset_index(drop=True)
    )
    filter_orgs.to_csv("data/projects.csv")
    # with open("data/stats.json", 'w') as file:
    #     json.dump(organizations, file)


def load_projects_info(path):
    return pd.read_csv(path)


def add_commit_hash(path_dir, path):
    data = load_projects_info(path)

    projects_info = merge_repos_lang_info(path_dir)
    test = {}
    aug_data = []
    for p in data.index:
        row = data.iloc[p]
        key = row["Organization"] + "/" + row["Name"] + "_" + row["Language"]
        if key in test:
            continue
        test[key] = True
        commit_hash = projects_info[key]["commit_hash"]
        new_row = list(row) + [commit_hash]
        aug_data.append(new_row)

    cols = list(data.columns) + ["Commit_hash"]
    df_aug_data = pd.DataFrame(aug_data, columns=cols)

    df_aug_data.to_csv(path_dir / Path("aug_projects_info.csv"))

    return df_aug_data


def add_ncloc_by_language(path, projects_path):
    data = load_projects_info(projects_path)

    aug_data = []
    for file in path.iterdir():
        if file.suffix == ".json" and file.stem.startswith("projects_cpp"):
            projects_by_lang = {}
            with open(file, "r") as fp:
                projects_by_lang_temp = json.load(fp)
                for p in projects_by_lang_temp:
                    projects_by_lang[p["id"]] = p
            for d in data.index:
                row = data.iloc[d]
                key = row.get("Name")
                lang = row.get("Language")
                if key not in projects_by_lang:
                    print(key)
                    continue
                ncloc_by_language = projects_by_lang[key]["metrics"][
                    "ncloc_by_language"
                ][lang]
                new_row = list(row) + [ncloc_by_language]
                aug_data.append(new_row)
                print(aug_data)
                time.sleep(2)

    cols = list(data.columns) + ["NCloc_by_language"]
    df_aug_data = pd.DataFrame(aug_data, columns=cols)

    df_aug_data.to_csv(path / Path("aug_projects_info_lines.csv"))

    return df_aug_data


def merge_repos_lang_info(path):
    projects_info = {}
    sum_ = 0
    for file in path.iterdir():
        if file.suffix == ".json" and file.stem.startswith("repos"):
            lang = file.stem.split("_")[-1]
            projects_lang_info = None
            with open(file, "r") as fp:
                projects_lang_info = json.load(fp)
            sum_ += len(projects_lang_info)
            for pi in projects_lang_info:
                if "url" in pi:
                    if (pi["full_name"] + "_" + lang) in projects_info:
                        print(pi["full_name"])
                    projects_info[pi["full_name"] + "_" + lang] = pi
    return projects_info


if __name__ == "__main__":
    # main()
    # merge_repos_lang_info(Path("data/"))
    # d = add_commit_hash(Path("data/"), Path("data/projects_info.csv"))
    # data = None
    # with open("data/projects_cpp.json", "r") as fp:
    #     data = json.load(fp)
    # pprint(data[1])
    d = add_ncloc_by_language(Path("data/"), Path("data/aug_projects_info.csv"))
