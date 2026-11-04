from app.ingestion.github_ingestion import get_repository_metadata, get_repository_tree, filter_repository_files, get_file_content

# metadata = get_repository_metadata("psf", "requests")


# print("Repository:", metadata["full_name"])
# print("Default branch:", metadata["default_branch"])

# tree_response = get_repository_tree(owner="psf", repository="requests", branch=metadata["default_branch"])

# tree = tree_response["tree"]

# print("\nTotal entries: ", len(tree))
# print("Tree truncated: ", tree_response["truncated"])

# filtered_files = filter_repository_files(tree)

# print("\nFiltered files: ", len(filtered_files))

# for item in filtered_files[:10]:
#     print(item["path"], item["size"])

readme = get_file_content(
    owner="psf",
    repository="requests",
    file_path="README.md",
)

print("\nREADME content:")
print(readme[:500])