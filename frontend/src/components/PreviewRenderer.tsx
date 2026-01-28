// import React from 'react';
//
// export interface AssetMap {
//   [key: string]: { type: string; src?: string; latex?: string };
// }
//
// export const PreviewRenderer = ({ rawText, assetsMap }: { rawText: string; assetsMap: AssetMap }) => {
//     const normalizedText = rawText ? rawText.normalize('NFC') : '';
//   const parseLine = (line: string) => {
//     // 1. Xử lý Bảng: [* Col 1 | Col 2 *]
//     // Trim() để xóa khoảng trắng thừa đầu cuối
//     const cleanLine = line.trim();
//     const tableRegex = /^\[\*\s*(.*?)\s*\*\]$/;
//
//     if (tableRegex.test(cleanLine)) {
//       const content = cleanLine.match(tableRegex)![1];
//       const cols = content.split('|');
//       return (
//         <div className="flex border-b border-gray-300 last:border-0 hover:bg-gray-50">
//           {cols.map((col, idx) => (
//              <div key={idx} className="flex-1 border-r border-gray-300 last:border-0 p-2 text-center">
//                {parseTokens(col)}
//              </div>
//           ))}
//         </div>
//       );
//     }
//
//     // Nếu không phải bảng, render dòng bình thường
//     return <div className="mb-2 leading-relaxed">{parseTokens(line)}</div>;
//   };
//
//   const parseTokens = (text: string) => {
//     // Regex bắt: [!b:...] HOẶC [img:$...$] HOẶC [!m:$...$]
//     const regex = /(\[!b:.*?\]|\[img:\$.*?\$\]|\[!m:\$.*?\$\])/g;
//     const parts = text.split(regex);
//
//     return parts.map((part, index) => {
//       // BOLD: [!b:text] (Độ dài header là 4: '[!b:')
//       if (part.startsWith('[!b:')) {
//         const content = part.slice(4, -1);
//         return <strong key={index} className="font-bold text-gray-900">{content}</strong>;
//       }
//
//       // IMAGE: [img:$id$] (Độ dài header là 5: '[img:$')
//       if (part.startsWith('[img:$')) {
//         const id = part.slice(6, -2); // Sửa thành 6 nếu header là [img:$
//         const asset = assetsMap[id];
//         if (asset && asset.src) {
//           //return <img key={index} src={asset.src} alt="img" className="block max-w-full my-2 border rounded" />;
//            return <img key={index} src={asset.src} alt="img" className="block max-w-[90%] mx-auto my-3" />;
//         }
//         return <span key={index} className="text-red-500 text-xs">[Ảnh lỗi]</span>;
//       }
//
//       // MATH: [!m:$id$] (Độ dài header là 5: '[!m:$')
//       // LỖI CŨ CỦA BẠN LÀ SLICE(6), NÊN NÓ MẤT CHỮ 'm' CỦA 'mathtype'
//       if (part.startsWith('[!m:$')) {
//         const id = part.slice(5, -2); // <--- SỬA QUAN TRỌNG: 5 thay vì 6
//         const asset = assetsMap[id];
//         return (
//             <span key={index} className="inline-block bg-blue-50 text-blue-700 px-1 rounded border border-blue-200 text-sm font-mono mx-1">
//                 {asset?.latex || `(Công thức: ${id})`}
//             </span>
//         );
//       }
//
//       return <span key={index}>{part}</span>;
//     });
//   };
//
//   return (
//     <div className="preview-content p-4 font-serif text-gray-800 text-lg">
//       {normalizedText.split('\n').map((line, i) => (
//         <React.Fragment key={i}>
//             {parseLine(line)}
//         </React.Fragment>
//       ))}
//     </div>
//   );
// };
//
// export default PreviewRenderer;
import React from 'react';

export interface AssetMap {
  [key: string]: { type: string; src?: string; latex?: string };
}

export const PreviewRenderer = ({ rawText, assetsMap }: { rawText: string; assetsMap: AssetMap }) => {

  // --- FIX LỖI FONT 1: CHUẨN HÓA UNICODE ---
  // Chuyển đổi các ký tự bị tách (như a + ´) thành ký tự gộp (á)
  const normalizedText = rawText ? rawText.normalize('NFC') : '';

  const parseLine = (line: string) => {
    const cleanLine = line.trim();
    // Regex bảng: [* Col1 | Col2 *]
    const tableRegex = /^\[\*\s*(.*?)\s*\*\]$/;

    if (tableRegex.test(cleanLine)) {
      const content = cleanLine.match(tableRegex)![1];
      const cols = content.split('|');
      return (
        <div className="flex border border-black border-collapse my-4">
          {cols.map((col, idx) => (
             <div key={idx} className="flex-1 border-r border-black last:border-0 p-2 text-center break-words">
               {parseTokens(col)}
             </div>
          ))}
        </div>
      );
    }
    return <div className="mb-2 leading-relaxed text-justify">{parseTokens(line)}</div>;
  };

  const parseTokens = (text: string) => {
    // Regex bắt: [!b:...] HOẶC [img:$...$] HOẶC [!m:$...$]
    const regex = /(\[!b:.*?\]|\[img:\$.*?\$\]|\[!m:\$.*?\$\])/g;
    const parts = text.split(regex);

    return parts.map((part, index) => {
      // BOLD
      if (part.startsWith('[!b:')) {
        const content = part.slice(4, -1);
        return <strong key={index} className="font-bold">{content}</strong>;
      }

      // IMAGE
      if (part.startsWith('[img:$')) {
        const id = part.slice(6, -2);
        const asset = assetsMap[id];
        if (asset && asset.src) {
          // Thêm style display block và margin auto để căn giữa ảnh
          return <img key={index} src={asset.src} alt="img" className="block max-w-[90%] mx-auto my-3" />;
        }
        return <span key={index} className="text-red-500 text-xs italic">[Ảnh lỗi]</span>;
      }

      // MATH / FORMULA
      if (part.startsWith('[!m:$')) {
        const id = part.slice(5, -2);
        const asset = assetsMap[id];
        // Hiển thị công thức đẹp hơn
        return (
            <span key={index} className="inline-block px-1 rounded mx-0.5 text-blue-800 font-serif italic font-medium">
                {asset?.latex ? ` ${asset.latex} ` : `(${id})`}
            </span>
        );
      }

      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="preview-content">
      {normalizedText.split('\n').map((line, i) => (
        <React.Fragment key={i}>
            {parseLine(line)}
        </React.Fragment>
      ))}
    </div>
  );
};

export default PreviewRenderer;