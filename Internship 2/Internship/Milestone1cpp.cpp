#include <xlnt/xlnt.hpp>

using namespace xlnt;

int main(){
    workbook wb;
    worksheet ws = wb.active_sheet();
    ws.cell("A1").value(5);
    ws.cell("B2").value("string data");
    ws.cell("C3").formula("=RAND()");
    ws.merge_cells("C3:C4");
    ws.freeze_panes("B2");
    wb.save("example.xlsx");
    return 0;
}