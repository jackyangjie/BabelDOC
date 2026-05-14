const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, PageNumber, BorderStyle, WidthType,
  ShadingType, VerticalAlign, HeadingLevel,
} = require("docx");

// ─── 示例对照翻译数据 ───
// 每项: { en: "原文段落", zh: "译文段落" }
const pairs = [
  {
    en: "Deep learning has revolutionized the field of natural language processing in recent years. Transformer-based architectures, in particular, have demonstrated remarkable performance across a wide range of NLP tasks, including machine translation, text summarization, and question answering.",
    zh: "近年来，深度学习彻底改变了自然语言处理领域。特别是基于 Transformer 的架构，在包括机器翻译、文本摘要和问答在内的广泛 NLP 任务中展现出了卓越的性能。",
  },
  {
    en: "The key innovation of the Transformer model lies in its self-attention mechanism, which allows the model to weigh the importance of different words in a sequence regardless of their positional distance. This addresses a fundamental limitation of previous recurrent neural network-based approaches.",
    zh: "Transformer 模型的关键创新在于其自注意力机制，它允许模型对序列中不同位置词语的重要性进行加权，不受位置距离的限制。这解决了以往基于循环神经网络的方法的一个根本局限。",
  },
  {
    en: "Despite their success, large language models face significant challenges. These include high computational costs, potential biases in training data, and the difficulty of interpreting model decisions. Researchers continue to explore methods to address these issues while improving model performance.",
    zh: "尽管取得了成功，大型语言模型仍面临重大挑战。这包括高昂的计算成本、训练数据中潜在的偏见，以及解释模型决策的困难。研究人员持续探索解决这些问题的方法，同时提升模型性能。",
  },
  {
    en: "Transfer learning has emerged as a powerful paradigm in NLP. By pre-training on large-scale corpora and then fine-tuning on specific downstream tasks, models can achieve strong performance even with limited labeled data. This approach has become the de facto standard in the field.",
    zh: "迁移学习已成为 NLP 中的一种强大范式。通过在大规模语料库上进行预训练，然后在特定下游任务上进行微调，模型即使在标注数据有限的情况下也能取得良好性能。这种方法已成为该领域的事实标准。",
  },
  {
    en: "Looking ahead, several promising research directions are shaping the future of NLP. These include multimodal learning, which combines text with other modalities such as images and audio; efficient model compression techniques; and the development of more robust evaluation benchmarks.",
    zh: "展望未来，几个有前景的研究方向正在塑造 NLP 的未来。这包括多模态学习（将文本与图像、音频等其他模态相结合）、高效的模型压缩技术，以及更稳健的评估基准的开发。",
  },
];

// ─── 表格边框设置 ───
const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: "D0D0D0" };
const noBorder = { style: BorderStyle.NONE, size: 0 };
const cellBorders = {
  top: noBorder,
  bottom: { style: BorderStyle.SINGLE, size: 4, color: "E8E8E8" },
  left: noBorder,
  right: noBorder,
};

// ─── 构建表格行 ───
function buildRow(pair, index) {
  const bgColor = index % 2 === 0 ? "FFFFFF" : "F8F9FA";
  return new TableRow({
    children: [
      // 左列：原文
      new TableCell({
        borders: cellBorders,
        width: { size: 4680, type: WidthType.DXA },
        shading: { fill: bgColor, type: ShadingType.CLEAR },
        verticalAlign: VerticalAlign.TOP,
        children: [
          new Paragraph({
            spacing: { before: 80, after: 80, line: 360 },
            children: [
              new TextRun({
                text: pair.en,
                font: "Calibri",
                size: 21, // 10.5pt
                color: "1A1A1A",
              }),
            ],
          }),
        ],
      }),
      // 右列：译文
      new TableCell({
        borders: cellBorders,
        width: { size: 4680, type: WidthType.DXA },
        shading: { fill: bgColor, type: ShadingType.CLEAR },
        verticalAlign: VerticalAlign.TOP,
        children: [
          new Paragraph({
            spacing: { before: 80, after: 80, line: 360 },
            children: [
              new TextRun({
                text: pair.zh,
                font: "DengXian",
                size: 21, // 10.5pt
                color: "2B579A",
              }),
            ],
          }),
        ],
      }),
    ],
  });
}

// ─── 构建文档 ───
async function main() {
  // 表头行
  const headerRow = new TableRow({
    tableHeader: true,
    children: [
      new TableCell({
        borders: {
          top: { style: BorderStyle.SINGLE, size: 8, color: "2B579A" },
          bottom: { style: BorderStyle.SINGLE, size: 12, color: "2B579A" },
          left: noBorder,
          right: { style: BorderStyle.SINGLE, size: 4, color: "D0D0D0" },
        },
        width: { size: 4680, type: WidthType.DXA },
        shading: { fill: "2B579A", type: ShadingType.CLEAR },
        verticalAlign: VerticalAlign.CENTER,
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 100, after: 100 },
            children: [
              new TextRun({
                text: "Original Text",
                bold: true,
                font: "Calibri",
                size: 22,
                color: "FFFFFF",
              }),
            ],
          }),
        ],
      }),
      new TableCell({
        borders: {
          top: { style: BorderStyle.SINGLE, size: 8, color: "2B579A" },
          bottom: { style: BorderStyle.SINGLE, size: 12, color: "2B579A" },
          left: noBorder,
          right: noBorder,
        },
        width: { size: 4680, type: WidthType.DXA },
        shading: { fill: "2B579A", type: ShadingType.CLEAR },
        verticalAlign: VerticalAlign.CENTER,
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 100, after: 100 },
            children: [
              new TextRun({
                text: "中文翻译",
                bold: true,
                font: "DengXian",
                size: 22,
                color: "FFFFFF",
              }),
            ],
          }),
        ],
      }),
    ],
  });

  const doc = new Document({
    styles: {
      default: {
        document: {
          run: { font: "Calibri", size: 21 },
        },
      },
      paragraphStyles: [
        {
          id: "Title",
          name: "Title",
          basedOn: "Normal",
          run: { size: 36, bold: true, color: "1A1A1A", font: "Calibri" },
          paragraph: {
            spacing: { before: 120, after: 240 },
            alignment: AlignmentType.CENTER,
          },
        },
        {
          id: "Subtitle",
          name: "Subtitle",
          basedOn: "Normal",
          run: { size: 24, color: "666666", font: "Calibri" },
          paragraph: {
            spacing: { before: 0, after: 360 },
            alignment: AlignmentType.CENTER,
          },
        },
      ],
    },
    sections: [
      {
        properties: {
          page: {
            margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
            size: { width: 15840, height: 12240 }, // A4 landscape (or use LANDSCAPE orientation)
          },
        },
        headers: {
          default: new Header({
            children: [
              new Paragraph({
                alignment: AlignmentType.RIGHT,
                spacing: { after: 0 },
                children: [
                  new TextRun({
                    text: "Bilingual Translation — 双语对照翻译",
                    font: "Calibri",
                    size: 18,
                    color: "999999",
                    italics: true,
                  }),
                ],
              }),
            ],
          }),
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { after: 0 },
                children: [
                  new TextRun({ text: "Page ", size: 18, color: "999999" }),
                  new TextRun({
                    children: [PageNumber.CURRENT],
                    size: 18,
                    color: "999999",
                  }),
                  new TextRun({
                    text: " of ",
                    size: 18,
                    color: "999999",
                  }),
                  new TextRun({
                    children: [PageNumber.TOTAL_PAGES],
                    size: 18,
                    color: "999999",
                  }),
                ],
              }),
            ],
          }),
        },
        children: [
          // 文档标题
          new Paragraph({
            heading: HeadingLevel.TITLE,
            children: [new TextRun("A Survey of Deep Learning in NLP")],
          }),
          new Paragraph({
            style: "Subtitle",
            children: [new TextRun("深度学习在自然语言处理中的应用综述")],
          }),
          // 分隔线
          new Paragraph({
            spacing: { before: 0, after: 200 },
            border: {
              bottom: { style: BorderStyle.SINGLE, size: 6, color: "2B579A" },
            },
            children: [],
          }),
          // 说明文字
          new Paragraph({
            spacing: { before: 0, after: 300 },
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({
                text: "Each row below presents the original text (left) alongside its Chinese translation (right).",
                font: "Calibri",
                size: 20,
                color: "888888",
                italics: true,
              }),
            ],
          }),
          // 对照表格
          new Table({
            columnWidths: [4680, 4680],
            rows: [headerRow, ...pairs.map((p, i) => buildRow(p, i))],
          }),
          // 页脚说明
          new Paragraph({
            spacing: { before: 400 },
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({
                text: "— Generated with BabelDOC —",
                font: "Calibri",
                size: 18,
                color: "BBBBBB",
                italics: true,
              }),
            ],
          }),
        ],
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  const outPath = "/home/yangjie/work/workspace/BabelDOC/bilingual_translation.docx";
  fs.writeFileSync(outPath, buffer);
  console.log(`✅ Document generated: ${outPath}`);
  console.log(`   Size: ${(buffer.length / 1024).toFixed(1)} KB`);
}

main().catch(console.error);
