# Living Software repository cards

The cards use the Enntity Lab paper cover’s fungal canopy and the Darkroom film’s plum, cream, lavender, and mint palette. The shared series label sits above a single rule. The product name uses Georgia, the one-line description uses Avenir Next, and Menlo sets the series label and repository address. Keep the left side quiet for text and the artwork on the right.

Use the 1280 × 400 banner at the top of the README and the 1280 × 640 card as the GitHub social preview. Keep the product name and its plain-language benefit together so both survive thumbnail reduction. Repeat the product name and benefit as image alt text.

To add a sibling, copy this directory’s artwork and the renderer into its repo. On macOS with Pillow installed, render both sizes with the new product name, benefit and GitHub address.

```sh
python scripts/render-brand.py --product 'Enngraft' \
  --subtitle 'Install from source. Repair where it runs.' \
  --repository 'github.com/Enntity/enngraft'
```

Review both images at thumbnail size. Use a short product-specific subtitle and keep important text clear of the image edge. Set the social card in the repository’s GitHub settings. Add the `living-software` topic so related products can be found together. The source artwork is the typography-free right crop of the paper cover, the same crop used in the film. See [media credits](../../NOTICE.md).
