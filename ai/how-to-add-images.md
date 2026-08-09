# How to add egg photos and train the model

This is the whole job, start to finish. You do not need to write any code.

---

## 1. Set up, once

You need Python installed. Then, from the folder where you cloned the repo:

```
python -m venv .venv
```

Turn it on. You have to do this every time you open a new terminal:

```
.venv\Scripts\activate
```

You will know it worked because your terminal line starts with `(.venv)`.

Now install what the scripts need. This takes a few minutes:

```
pip install -r ai/requirements.txt
```

That is the setup done. Next time you come back, you only need the `activate` line.

---

## 2. Where the photos go

After cloning you already have three folders:

```
ai/dataset/good/
ai/dataset/defective/
ai/dataset/not_an_egg/
```

Put every photo into one of those three, based on what the photo shows.

| Folder | Put a photo here when |
|---|---|
| `good/` | It is an egg and you see nothing wrong inside it. |
| `defective/` | It is an egg and you see **any** problem: a blood spot, a meat spot, a big crack that light leaks through, or obvious shell damage. It does not matter which problem, they all go here. |
| `not_an_egg/` | There is no egg. Empty platform, your hand in the way, something dropped on the platform, a photo you took by mistake. |

**Do not rename these folders and do not add a fourth one.** The folder names are not labels for us to read. The training script reads them directly and turns them into the words the finished system prints on screen and saves to the database. If you rename `defective` to `defects`, the system starts saying "defects" everywhere and nothing warns you.

Filenames do not matter at all. `IMG_0041.jpg` is fine.

---

## 3. How to take the photos

**This part decides whether the model works, so it matters more than the number of photos.**

Every photo has to be taken the same way: same station, same candling light, same camera position, egg in the same spot. The model learns whatever is consistent in the images. If the good eggs are shot at the station and the defective ones are shot on a table by a window, the model learns "station versus window" instead of "good versus defective", and it will look accurate in testing and fail in real use.

The same rule catches people out on `not_an_egg`. Those photos must also be taken at the station with the candling light on, just with no egg there. **Do not** photograph a mug on a desk. The whole point of that folder is to recognise an empty platform under candling light, so that is what it has to be shown.

---

## 4. How many

Aim for **100 photos in each folder.** Below about 100 the model is guessing.

**Try hard to keep the three folders roughly even.** This is the part that goes wrong. Good eggs are easy to find and defective ones are not, so it is very easy to end up with 300 good and 20 defective. If that happens, the model learns it can just answer "good" every single time and still be right most of the time. It will report a great score and be useless, because catching defects is the entire reason the system exists.

Blood spots and meat spots cannot be bought on demand. **Start collecting those first**, and if you end up with only 40 of them, cut the other two folders down to about 40 as well rather than leaving it lopsided.

---

## 5. Train the model

Run this **from the top folder of the repo**, not from inside `ai/`:

```
python ai/training/train.py
```

It prints its progress and finishes by saving the model. If it errors immediately saying it found no images, you are either in the wrong folder or a folder is empty.

## 6. Try it on one photo

```
python ai/inference/classify.py path/to/some_photo.jpg
```

It prints one line, like:

```
{"image": "egg_0042.jpg", "class": "defective", "confidence": 0.91}
```

---

## 7. Two things to watch out for

**Confidence is not accuracy.** The `confidence` number above is only how sure the model is about that one photo. It is not a score for the model. A model can be confidently wrong.

**Do not report the training score as the system's accuracy.** The number the training run prints is measured on photos it already learned from, so it is always flattering. The paper claims 85% accuracy, and that figure has to come from photos the model has never seen. Send the images to M and let the scoring happen separately.

---

## 8. Sending the photos over

The photos are deliberately kept out of GitHub, so committing them will not work and is not a mistake you can make by accident. Zip the `ai/dataset` folder and send it, or share the folder, whichever is easier. Keep the three folders intact inside the zip.

If you find a public egg dataset online, send the link before using it. Most egg photo collections online are ordinary photos of the outside of eggs, and ours are candling photos with light shining through them. The two look nothing alike and mixing them in makes the model worse, so it needs a look first.
