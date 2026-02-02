
const hasUppercaseAnswerPattern = (line) => {
    const trimmed = line.trim();
    const regex = /(\*?)([A-D])[.\)]/g;
    let match;
    console.log(`Testing line: "${line}"`);

    while ((match = regex.exec(trimmed)) !== null) {
        const letterIndex = match.index + match[1].length;
        const charBefore = letterIndex > 0 ? trimmed[letterIndex - 1] : '';

        console.log(`  Match: "${match[0]}", Index: ${match.index}, Group1: "${match[1]}", Letter: "${match[2]}"`);
        console.log(`  LetterIndex: ${letterIndex}, CharBefore: "${charBefore}" (Code: ${charBefore.charCodeAt(0)})`);

        if (charBefore === ']' || charBefore === ':' || /\d/.test(charBefore)) {
            console.log("  -> Skipped due to invalid CharBefore");
            continue;
        }

        if (charBefore === '' || charBefore === ' ' || charBefore === '\t' || charBefore === '*') {
            console.log("  -> Matched!");
            return true;
        } else {
            console.log("  -> Failed secondary CharBefore check");
        }
    }
    return false;
};

// Test cases
console.log("Result:", hasUppercaseAnswerPattern("*A. This is a selected answer"));
console.log("Result:", hasUppercaseAnswerPattern("A. This is a normal answer"));
console.log("Result:", hasUppercaseAnswerPattern("Câu 1. *A. Inline answer"));
console.log("Testing NBSP (Code 160):");
const nbspLine = "*\u00A0A. Answer with NBSP";
console.log(`Line: "${nbspLine}"`);
console.log("Result:", hasUppercaseAnswerPattern(nbspLine));

console.log("--- Testing Pure Regex Approach ---");
const pureRegex = /(?:^|[\s*])\*?[A-D][.\)]/;
console.log("Pattern: /(?:^|[\\s*])\\*?[A-D][.\\)]/");
const test = (str) => console.log(`"${str}" -> ${pureRegex.test(str.trim())}`);
test("*A. Content");
test("A. Content");
test("Câu 1. *A. Content");
test("WordEndA. Content"); // Should be false
test("WordEnd*A. Content"); // Should be true? Or false? "End*A." is weird.


