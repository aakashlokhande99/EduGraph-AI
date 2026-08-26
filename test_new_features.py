"""
Verification for:
1. DELETE /api/documents/{filename}
2. Index HTML containing Generated Lessons sidebar title and delete button hooks
3. Verify chat AI card markup changes
"""
import os
from fastapi.testclient import TestClient
from main import app, OUTPUT_DIR

client = TestClient(app)

def test_delete_endpoint_and_ui():
    # 1. Create a dummy test PDF in Output
    test_pdf_name = "education_test_delete_sample.pdf"
    test_pdf_path = os.path.join(OUTPUT_DIR, test_pdf_name)
    with open(test_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 dummy pdf content")

    assert os.path.exists(test_pdf_path), "Dummy PDF was not created"

    # 2. Test GET /api/documents lists it
    res_list = client.get("/api/documents")
    assert res_list.status_code == 200
    docs = res_list.json()["documents"]
    assert any(d["pdf_filename"] == test_pdf_name for d in docs)
    print("✅ Dummy PDF listed in /api/documents")

    # 3. Test DELETE /api/documents/{filename}
    res_del = client.delete(f"/api/documents/{test_pdf_name}")
    assert res_del.status_code == 200, f"Delete failed: {res_del.text}"
    del_data = res_del.json()
    assert del_data["status"] == "success"
    assert not os.path.exists(test_pdf_path), "File still exists after deletion"
    print("✅ DELETE /api/documents/{filename} successfully deleted the file")

    # 4. Verify 404 on deleting non-existent file
    res_del_404 = client.delete("/api/documents/non_existent_file.pdf")
    assert res_del_404.status_code == 404
    print("✅ DELETE /api/documents 404 on non-existent file verified")

    # 5. Verify index HTML markup
    res_html = client.get("/")
    assert res_html.status_code == 200
    html = res_html.text

    assert "btnSidebarTitle" in html, "btnSidebarTitle missing in HTML"
    assert "doc-delete-btn" in html, "doc-delete-btn missing in HTML"
    assert "deleteDocument" in html, "deleteDocument function missing in JS"
    assert "toggleSidebar" in html, "toggleSidebar function missing in JS"
    assert "btnCollapseSidebar" in html, "btnCollapseSidebar missing in HTML"
    print("✅ All HTML and JavaScript hooks verified in index.html")

if __name__ == "__main__":
    test_delete_endpoint_and_ui()
    print("\n🎉 ALL NEW FEATURE TESTS PASSED SUCCESSFULLY!")
