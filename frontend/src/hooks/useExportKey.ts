import { useMutation } from '@tanstack/react-query';
import { examApi } from '../api';

export const useExportKey = () => {
    return useMutation({
        mutationFn: (rawText: string) => examApi.exportKey(rawText),
        onSuccess: (blob) => {
            // Create a link and click it to download
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'Dap_An_Goc.xlsx');
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);
        },
        onError: (error) => {
            console.error("Export Failed:", error);
            alert("Lỗi khi xuất file Excel: " + (error instanceof Error ? error.message : String(error)));
        }
    });
};
