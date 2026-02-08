import React, { useMemo } from 'react';
import { Check, X } from 'lucide-react';
import katex from 'katex';
import 'katex/dist/katex.min.css';

export interface AssetMap {
  [key: string]: { type: string; src?: string; latex?: string };
}

interface PreviewRendererProps {
  rawText: string;
  assetsMap: AssetMap;
  correctAnswers?: Map<number, string>;
  onAnswerSelect?: (questionIndex: number, answer: string, sourceLineNumber: number, answerLineNumber: number) => void;
  trueFalseAnswers?: Map<string, boolean>;
  onTrueFalseToggle?: (questionIndex: number, letter: string, sourceLineNumber: number, answerLineNumber: number) => void;
  onShortAnswerChange?: (questionIndex: number, text: string, sourceLineNumber: number) => void;
  onLineClick?: (lineNumber: number) => void;
}

// ... (lines 20-358 unchanged - skipping context for brevity in tool call, will target specific blocks if possible or use multiple chunks)
// Wait, replace_file_content is better for contiguous.
// The file is small enough to perhaps do one block if I include the middle? 
// Actually, let's just do the QuestionCard component logic first since interfaces are separated.
// But interfaces are at top.
// Let's use multi_replace for this to be clean.


// --- Types for Parsed Structure ---
interface QuestionData {
  index: number;
  type: 'multiplechoice' | 'truefalse' | 'shortanswer';
  contentLines: string[];
  uppercaseAnswers: { letter: string; content: string; isCorrect: boolean; lineNumber: number }[];
  lowercaseAnswers: { letter: string; content: string; isCorrect: boolean; lineNumber: number }[];
  sourceLineNumber: number;
}

type ParsedBlock =
  | { type: 'part-header1' | 'part-header2' | 'part-header3', id: string, content: string }
  | { type: 'question', id: string, data: QuestionData }
  | { type: 'text', id: string, content: string };

// --- Constants & Helpers ---
// Allow optional [ID:xxx] prefix before Câu
const QUESTION_REGEX = /(?:\[ID:[^\]]*\]\s*)?Câu\s*(\d+)/i;

const stripFormatMarkers = (text: string): string => {
  return text.replace(/\[!b:/g, '').replace(/\]/g, '').replace(/\[!/g, '');
};

const cleanContentText = (text: string): string => {
  let cleaned = text.replace(/\[\*\s*/g, '');
  cleaned = cleaned.replace(/\s*\*\]/g, '');
  cleaned = cleaned.replace(/\[!b:([^\]]*)\]/g, '$1');
  cleaned = cleaned.replace(/\[!(?!m:|b:)/g, '');
  return cleaned;
};

// Detect Part headers
const isPart1Header = (text: string): boolean => {
  const stripped = stripFormatMarkers(text);
  const lower = stripped.toLowerCase();
  if (lower.includes('đúng sai') || lower.includes('trả lời ngắn') ||
    lower.includes('phần ii') || lower.includes('phần 2') ||
    lower.includes('phần iii') || lower.includes('phần 3')) return false;
  return lower.includes('phần i') || lower.includes('phần 1') ||
    lower.includes('trắc nghiệm nhiều phương án') || lower.includes('trắc nghiệm lựa chọn');
};

const isPart2Header = (text: string): boolean => {
  const stripped = stripFormatMarkers(text);
  const lower = stripped.toLowerCase();
  if (lower.includes('trả lời ngắn') || lower.includes('phần iii') || lower.includes('phần 3')) return false;
  return lower.includes('phần ii') || lower.includes('phần 2') ||
    lower.includes('đúng sai') || lower.includes('trắc nghiệm đ/s');
};

const isPart3Header = (text: string): boolean => {
  const stripped = stripFormatMarkers(text);
  const lower = stripped.toLowerCase();
  return lower.includes('phần iii') || lower.includes('phần 3') ||
    lower.includes('trả lời ngắn') || lower.includes('tự luận') ||
    lower.includes('trắc nghiệm trả lời ngắn') ||
    lower.includes('điền đáp án') || lower.includes('trả lời câu hỏi');
};

const isJustMarker = (line: string): boolean => {
  const trimmed = line.trim();
  return trimmed === '[*' || trimmed === '*]' || trimmed === '|' || trimmed === '*';
};

const isEndMarker = (line: string): boolean => {
  const trimmed = line.trim();
  const stripped = trimmed.replace(/\[!b:/g, '').replace(/\]/g, '');
  const upper = stripped.toUpperCase();
  return /^[-=\s]*HẾT[-=\s]*$/.test(upper);
};

// Answer Pattern Detection Methods (Pure Logic)
const hasUppercaseAnswerPattern = (line: string): boolean => {
  const trimmed = line.trim();
  // eslint-disable-next-line no-useless-escape
  const regex = /(\*?)([A-H])[.\)]/g;
  let match;
  while ((match = regex.exec(trimmed)) !== null) {
    const letterIndex = match.index + match[1].length;
    const charBefore = letterIndex > 0 ? trimmed[letterIndex - 1] : '';
    if (charBefore === ']' || charBefore === ':' || /\d/.test(charBefore)) continue;
    // FIX: Only skip if digit is IMMEDIATELY before space (e.g., "2,5 A."), 
    // but allow other chars before space (e.g., "đặc. B." is valid)
    if (/\s/.test(charBefore)) {
      const charBeforeSpace = letterIndex > 1 ? trimmed[letterIndex - 2] : '';
      if (/[0-9]/.test(charBeforeSpace)) continue;  // Only skip for digits, not dots/commas
    }
    if (charBefore === '' || /\s/.test(charBefore) || charBefore === '*') return true;
  }
  return false;
};

const hasLowercaseAnswerPattern = (line: string): boolean => {
  const trimmed = line.trim();
  // eslint-disable-next-line no-useless-escape
  // PART 2 STRICT: Only a-d and ')'
  return /(?:^|\s)(\*?)[a-d]\)\s*\S/.test(trimmed);
};

const extractUppercaseAnswers = (line: string): { letter: string; content: string; isMarkedCorrect: boolean }[] => {
  const answers: { letter: string; content: string; isMarkedCorrect: boolean }[] = [];
  const trimmedLine = line.trim();
  const markers: { index: number; letter: string; isMarkedCorrect: boolean; markerLength: number }[] = [];
  // eslint-disable-next-line no-useless-escape
  const regex = /(\*?)([A-H])[.\)]\s*/g;
  let match;
  while ((match = regex.exec(trimmedLine)) !== null) {
    const letterIndex = match.index + match[1].length;
    const charBefore = letterIndex > 0 ? trimmedLine[letterIndex - 1] : '';
    if (charBefore === ']' || charBefore === ':' || /\d/.test(charBefore)) continue;
    // FIX: Only skip if digit is IMMEDIATELY before space (e.g., "2,5 A."), 
    // but allow other chars before space (e.g., "đặc. B." is valid)
    if (/\s/.test(charBefore)) {
      const charBeforeSpace = letterIndex > 1 ? trimmedLine[letterIndex - 2] : '';
      if (/[0-9]/.test(charBeforeSpace)) continue;  // Only skip for digits, not dots/commas
    }
    if (charBefore === '' || /\s/.test(charBefore) || charBefore === '*') {
      markers.push({
        index: match.index,
        letter: match[2].toUpperCase(),
        isMarkedCorrect: match[1] === '*',
        markerLength: match[0].length
      });
    }
  }
  for (let i = 0; i < markers.length; i++) {
    const startIdx = markers[i].index + markers[i].markerLength;
    const endIdx = i < markers.length - 1 ? markers[i + 1].index : trimmedLine.length;
    answers.push({
      letter: markers[i].letter,
      content: trimmedLine.slice(startIdx, endIdx).trim(),
      isMarkedCorrect: markers[i].isMarkedCorrect
    });
  }
  return answers;
};

const extractLowercaseAnswers = (line: string): { letter: string; content: string; isMarkedCorrect: boolean }[] => {
  const answers: { letter: string; content: string; isMarkedCorrect: boolean }[] = [];
  const trimmedLine = line.trim();
  const markers: { index: number; letter: string; isMarkedCorrect: boolean; fullMatch: string }[] = [];
  // eslint-disable-next-line no-useless-escape
  // PART 2 STRICT: Only a-d and ')'
  const regex = /(\*?)([a-d])\)\s*/g;
  let match;
  while ((match = regex.exec(trimmedLine)) !== null) {
    // Need similar charBefore check for safety? regex (?:^|\s) handles it mostly.
    // But let's rely on regex here as it includes \s check
    markers.push({
      index: match.index,
      letter: match[2].toLowerCase(),
      isMarkedCorrect: match[1] === '*',
      fullMatch: match[0]
    });
  }
  for (let i = 0; i < markers.length; i++) {
    const startIdx = markers[i].index + markers[i].fullMatch.length;
    const endIdx = i < markers.length - 1 ? markers[i + 1].index : trimmedLine.length;
    answers.push({
      letter: markers[i].letter,
      content: trimmedLine.slice(startIdx, endIdx).trim(),
      isMarkedCorrect: markers[i].isMarkedCorrect
    });
  }
  return answers;
};

// --- CORE PARSER FUNCTION (Pure, Memoizable) ---
const parseDocumentBlocks = (rawText: string): ParsedBlock[] => {
  const normalizedText = rawText ? rawText.normalize('NFC') : '';
  const lines = normalizedText.split('\n');
  const blocks: ParsedBlock[] = [];

  let currentPart = 1;
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmedLine = line.trim();

    if (trimmedLine === '' || isJustMarker(trimmedLine)) {
      i++; continue;
    }

    // Header Detection
    if (isPart1Header(trimmedLine)) {
      currentPart = 1;
      blocks.push({ type: 'part-header1', id: `ph1-${i}`, content: cleanContentText(trimmedLine) });
      i++; continue;
    }
    if (isPart2Header(trimmedLine)) {
      currentPart = 2;
      blocks.push({ type: 'part-header2', id: `ph2-${i}`, content: cleanContentText(trimmedLine) });
      i++; continue;
    }
    if (isPart3Header(trimmedLine)) {
      currentPart = 3;
      blocks.push({ type: 'part-header3', id: `ph3-${i}`, content: cleanContentText(trimmedLine) });
      i++; continue;
    }

    // Question Detection
    const questionMatch = trimmedLine.match(QUESTION_REGEX);
    if (questionMatch) {
      const qIndex = parseInt(questionMatch[1], 10);
      const qStartLine = i + 1;

      const qContentLines: string[] = [];
      const upAnswers: any[] = [];
      const lowAnswers: any[] = [];

      // Header Text
      let headerContent = trimmedLine.replace(QUESTION_REGEX, '').replace(/^[\.:]\s*/, '').trim();
      headerContent = cleanContentText(headerContent);
      if (headerContent && !isJustMarker(headerContent)) {
        qContentLines.push(headerContent);
      }
      i++;

      // Scan content loop
      while (i < lines.length) {
        const currLine = lines[i];
        const currTrimmed = currLine.trim();

        if (currTrimmed.match(QUESTION_REGEX) ||
          isPart1Header(currTrimmed) ||
          isPart2Header(currTrimmed) ||
          isPart3Header(currTrimmed) ||
          isEndMarker(currTrimmed)) {
          break;
        }
        if (isJustMarker(currTrimmed) || currTrimmed === '') {
          i++; continue;
        }

        // Answer extraction logic
        // PART 1: Uppercase Answers Only (A, B, C, D)
        if (currentPart === 1 && hasUppercaseAnswerPattern(currTrimmed)) {
          const extracted = extractUppercaseAnswers(currTrimmed);
          extracted.forEach(a => upAnswers.push({
            letter: a.letter, content: a.content, isCorrect: a.isMarkedCorrect, lineNumber: i + 1
          }));
          i++;
        }
        // PART 2: Lowercase Answers Only (a, b, c, d)
        else if (currentPart === 2 && hasLowercaseAnswerPattern(currTrimmed)) {
          const extracted = extractLowercaseAnswers(currTrimmed);
          extracted.forEach(a => lowAnswers.push({
            letter: a.letter, content: a.content, isCorrect: a.isMarkedCorrect, lineNumber: i + 1
          }));
          i++;
        } else {
          // Content line
          // Should we check for Uppercase in Part 2? Usually no.
          // Should we check for Lowercase in Part 1? NO (This fixes Q2 issue).
          const cleaned = cleanContentText(currLine);
          if (cleaned.trim() && !isJustMarker(cleaned.trim())) {
            qContentLines.push(cleaned);
          }
          i++;
        }
      }

      // Determine Type
      let qType: 'multiplechoice' | 'truefalse' | 'shortanswer' = 'multiplechoice';
      if (currentPart === 3) qType = 'shortanswer';
      else if (lowAnswers.length > 0) qType = 'truefalse';

      blocks.push({
        type: 'question',
        id: `q-${qIndex}-${qStartLine}`,
        data: {
          index: qIndex,
          type: qType,
          contentLines: qContentLines,
          uppercaseAnswers: upAnswers,
          lowercaseAnswers: lowAnswers,
          sourceLineNumber: qStartLine
        }
      });
    } else {
      // Normal text
      const cleaned = cleanContentText(trimmedLine);
      if (cleaned && !isJustMarker(cleaned)) {
        blocks.push({ type: 'text', id: `txt-${i}`, content: cleaned });
      }
      i++;
    }
  }
  return blocks;
};

// --- PREVIEW RENDERER (Main Component) ---
export const PreviewRenderer: React.FC<PreviewRendererProps> = ({
  rawText,
  assetsMap,
  correctAnswers = new Map(),
  onAnswerSelect,
  trueFalseAnswers = new Map(),
  onTrueFalseToggle,
  onShortAnswerChange,
  onLineClick
}) => {
  // Memoize structure calculation!
  const blocks = useMemo(() => parseDocumentBlocks(rawText), [rawText]);

  return (
    <div className="preview-content">
      {blocks.map((block) => {
        if (block.type === 'part-header1' || block.type === 'part-header2' || block.type === 'part-header3') {
          return (
            <div key={block.id} className="mb-4 p-3 border border-blue-200 rounded-lg bg-blue-50">
              <div className="font-semibold text-blue-700">{block.content}</div>
            </div>
          );
        }
        if (block.type === 'text') {
          return (
            <div key={block.id} className="mb-2 leading-relaxed text-justify">
              {parseTokens(block.content, assetsMap)}
            </div>
          );
        }
        if (block.type === 'question') {
          const d = block.data;
          // Resolve correctness from state maps
          const finalUpAnswers = d.uppercaseAnswers.map(a => ({
            ...a,
            isCorrect: a.isCorrect || correctAnswers.get(d.index) === a.letter
          }));
          const finalLowAnswers = d.lowercaseAnswers.map(a => ({
            ...a,
            isCorrect: a.isCorrect || trueFalseAnswers.get(`${d.index}-${a.letter}`) === true
          }));

          return (
            <QuestionCard
              key={block.id}
              questionIndex={d.index}
              questionType={d.type}
              contentLines={d.contentLines}
              uppercaseAnswers={finalUpAnswers}
              lowercaseAnswers={finalLowAnswers}
              assetsMap={assetsMap}
              onAnswerSelect={onAnswerSelect}
              onTrueFalseToggle={onTrueFalseToggle}
              onShortAnswerChange={onShortAnswerChange}
              parseTokens={parseTokens}
              sourceLineNumber={d.sourceLineNumber}
              onLineClick={onLineClick}
              currentAnswer={correctAnswers.get(d.index)} // Pass current answer for Short Answer input
            />
          );
        }
        return null;
      })}
    </div>
  );
};

// --- SUB-COMPONENTS (QuestionCard, Option, parseTokens implementation) ---
// (Keeping mostly original implementation but ensuring interfaces match)

interface QuestionCardProps {
  questionIndex: number;
  questionType: 'multiplechoice' | 'truefalse' | 'shortanswer';
  contentLines: string[];
  uppercaseAnswers: { letter: string; content: string; isCorrect: boolean; lineNumber: number }[];
  lowercaseAnswers: { letter: string; content: string; isCorrect: boolean; lineNumber: number }[];
  assetsMap: AssetMap;
  onAnswerSelect?: (questionIndex: number, answer: string, sourceLineNumber: number, answerLineNumber: number) => void;
  onTrueFalseToggle?: (questionIndex: number, letter: string, sourceLineNumber: number, answerLineNumber: number) => void;
  onShortAnswerChange?: (questionIndex: number, text: string, sourceLineNumber: number) => void;
  parseTokens: (text: string, assetsMap: AssetMap) => React.ReactNode;
  sourceLineNumber: number;
  onLineClick?: (lineNumber: number) => void;
  currentAnswer?: string;
}

const QuestionCard: React.FC<QuestionCardProps> = ({
  questionIndex,
  questionType,
  contentLines,
  uppercaseAnswers,
  lowercaseAnswers,
  assetsMap,
  onAnswerSelect,
  onTrueFalseToggle,
  onShortAnswerChange,
  parseTokens,
  sourceLineNumber,
  onLineClick,
  currentAnswer
}) => {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // Stop bubble just in case
    if (onLineClick) onLineClick(sourceLineNumber);
  };

  return (
    <div className="question-card mb-6 rounded-lg p-2 -m-2">
      {/* Header - Clickable for sync */}
      <div
        className="question-header flex items-center gap-2 mb-3 flex-wrap cursor-pointer hover:opacity-80 transition-opacity w-fit"
        onClick={handleClick}
        title="Click để xem trong editor"
      >
        <span className="question-number bg-gray-100 text-gray-700 px-3 py-1.5 rounded-full text-sm font-semibold border border-gray-200">
          Câu {questionIndex}.
        </span>
      </div>

      {contentLines.length > 0 && (
        <div
          className="question-content-box border border-gray-200 rounded-lg p-4 mb-4 bg-white cursor-pointer hover:border-blue-400 hover:shadow-sm transition-all"
          onClick={handleClick}
          title="Click để xem trong editor"
        >
          {contentLines.map((line, idx) => (
            <div key={idx} className="leading-relaxed mb-1 last:mb-0">
              {parseTokens(line, assetsMap)}
            </div>
          ))}
        </div>
      )}

      {uppercaseAnswers.length > 0 && (
        <div className="answer-options space-y-2">
          {uppercaseAnswers.map((answer) => (
            <MultipleChoiceOption
              key={answer.letter}
              letter={answer.letter}
              content={answer.content}
              isCorrect={answer.isCorrect}
              onClick={() => onAnswerSelect?.(questionIndex, answer.letter, sourceLineNumber, answer.lineNumber)}
              parseTokens={(text) => parseTokens(text, assetsMap)}
            />
          ))}
        </div>
      )}

      {lowercaseAnswers.length > 0 && (
        <div className="answer-options space-y-2">
          {lowercaseAnswers.map((answer) => (
            <TrueFalseOption
              key={answer.letter}
              letter={answer.letter}
              content={answer.content}
              isTrue={answer.isCorrect}
              onClick={() => onTrueFalseToggle?.(questionIndex, answer.letter, sourceLineNumber, answer.lineNumber)}
              parseTokens={(text) => parseTokens(text, assetsMap)}
            />
          ))}
        </div>
      )}

      {questionType === 'shortanswer' && (
        <div className="answer-input-section mt-4">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-700">Đáp án:</span>
            <input
              type="text"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              placeholder="Nhập đáp án..."
              value={currentAnswer || ''}
              onChange={(e) => onShortAnswerChange?.(questionIndex, e.target.value, sourceLineNumber)}
            // No onClick needed here, parent doesn't capture anymore
            />
          </div>
        </div>
      )}
    </div>
  );
};

// ... Option Components ...
interface MultipleChoiceOptionProps {
  letter: string; content: string; isCorrect: boolean; onClick: () => void; parseTokens: (text: string) => React.ReactNode;
}
const MultipleChoiceOption: React.FC<MultipleChoiceOptionProps> = ({ letter, content, isCorrect, onClick, parseTokens }) => {
  return (
    <div className="answer-option flex items-center gap-2 cursor-pointer transition-all duration-200 py-1" onClick={onClick}>
      <div className={`answer-check w-5 flex-shrink-0 flex items-center justify-center ${isCorrect ? 'text-blue-600' : 'text-transparent'}`}>
        {isCorrect && <Check size={16} strokeWidth={3} />}
      </div>
      <div className={`answer-letter w-7 h-7 flex items-center justify-center rounded font-medium text-sm border flex-shrink-0 transition-all ${isCorrect ? 'bg-blue-50 text-blue-700 border-blue-400' : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'}`}>
        {letter}
      </div>
      <div className={`answer-content py-1 px-2 rounded border transition-all flex-1 ${isCorrect ? 'border-blue-400 bg-blue-50 text-blue-800' : 'border-gray-200 bg-white hover:border-gray-300'}`}>
        {parseTokens(content)}
      </div>
    </div>
  );
};

interface TrueFalseOptionProps {
  letter: string; content: string; isTrue: boolean; onClick: () => void; parseTokens: (text: string) => React.ReactNode;
}
const TrueFalseOption: React.FC<TrueFalseOptionProps> = ({ letter, content, isTrue, onClick, parseTokens }) => {
  return (
    <div className="answer-option flex items-center gap-2 cursor-pointer transition-all duration-200 py-1" onClick={onClick}>
      <div className={`answer-check w-5 flex-shrink-0 flex items-center justify-center ${isTrue ? 'text-blue-600' : 'text-red-500'}`}>
        {isTrue ? <Check size={16} strokeWidth={3} /> : <X size={16} strokeWidth={2} />}
      </div>
      <div className={`answer-letter w-7 h-7 flex items-center justify-center rounded font-medium text-sm border flex-shrink-0 transition-all ${isTrue ? 'bg-blue-50 text-blue-700 border-blue-400' : 'bg-white text-gray-600 border-gray-300 hover:border-red-400'}`}>
        {letter})
      </div>
      <div className={`answer-content py-1 px-2 rounded border transition-all flex-1 ${isTrue ? 'border-blue-400 bg-blue-50 text-blue-800' : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'}`}>
        {parseTokens(content)}
      </div>
    </div>
  );
};

// ... parseTokens ...
const parseTokens = (text: string, assetsMap: AssetMap): React.ReactNode => {
  let cleanText = cleanContentText(text);
  if (!cleanText.trim()) return null;
  const regex = /(\[!b:.*?\]|\[img:\$.*?\$\]|\[!m:\$.*?\$\]|\$[^\$]+\$)/g;
  const parts = cleanText.split(regex);

  return parts.map((part, index) => {
    if (part.startsWith('$') && part.endsWith('$') && part.length > 2) {
      const latex = part.slice(1, -1);
      try {
        const html = katex.renderToString(latex, { throwOnError: false, displayMode: false, output: 'html' });
        return <span key={index} className="inline-block mx-0.5" dangerouslySetInnerHTML={{ __html: html }} />;
      } catch { return <span key={index}>{part}</span>; }
    }
    if (part.startsWith('[!b:')) {
      const content = part.slice(4, -1);
      return <strong key={index} className="font-bold">{content}</strong>;
    }
    if (part.startsWith('[img:$')) {
      const id = part.slice(6, -2);
      const asset = assetsMap[id];
      if (asset && asset.src) return <img key={index} src={asset.src} alt="img" className="block max-w-full my-2 rounded" />;
      return <span key={index} className="text-red-500 text-xs italic">[Ảnh lỗi]</span>;
    }
    if (part.startsWith('[!m:$')) {
      const id = part.slice(5, -2);
      const asset = assetsMap[id];
      if (asset?.latex) {
        try {
          const html = katex.renderToString(asset.latex, { throwOnError: false, displayMode: false, output: 'html' });
          return <span key={index} className="inline-block mx-0.5" dangerouslySetInnerHTML={{ __html: html }} />;
        } catch {
          return <span key={index} className="inline-block px-2 py-0.5 rounded bg-fuchsia-50 border border-fuchsia-200 mx-0.5"><span className="text-fuchsia-600 font-mono text-sm">{asset.latex}</span></span>;
        }
      }
      if (asset?.src) {
        return <img key={index} src={asset.src} alt="math" className="inline-block h-[1.2em] align-middle mx-0.5" style={{ verticalAlign: 'middle' }} />;
      }
      return <span key={index} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-fuchsia-50 border border-fuchsia-200 mx-0.5" title={`MathType ID: ${id}`}><span className="text-[10px] font-bold text-white bg-fuchsia-500 px-1 rounded">CT</span><span className="text-fuchsia-700 font-mono text-sm">{id}</span></span>;
    }
    return <span key={index}>{part}</span>;
  });
};

export default PreviewRenderer;
