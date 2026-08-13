# How to add egg photos and train the model

This is the whole job, start to finish. You do not need to write any code.

---

## 1. Set up, once

**There are two different setups, and most people only need the small one.**

### If you are only taking photos

One install, and any Python version works:

```
pip install opencv-python
```

That is genuinely all. You do **not** need TensorFlow to take pictures, and skipping it saves you a
download of several hundred megabytes and the version problem below.

### If you are training the model

⚠️ **TensorFlow does not work on Python 3.14.** There is no build for it — `pip` will just say
*"No matching distribution found for tensorflow"* and there is nothing you can do about that except
use an older Python. **Use 3.13.** Check what you have with `py --list`.

From the folder where you cloned the repo, make a private space for the packages:

```
py -V:3.13 -m venv .venv
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

**The easy way is to let the capture script file them for you** — see section 3a. It saves straight
into the right folder as you shoot, so you never move a file by hand. Copying photos in yourself
still works fine if you already have them.

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

## 3a. Shooting with the capture script

Run this from the top folder of the repo, with your own name as the tag:

```
py ai/capture.py --tag yourname
```

A window opens showing what the webcam sees, live. Put an egg on the candler, **look at it, decide
what it is, and press one key:**

| Key | Saves the picture into |
|---|---|
| **G** | `good/` |
| **D** | `defective/` |
| **N** | `not_an_egg/` |
| **Q** | quit |

That is the whole interface. The photo is saved instantly into the right folder, and the running
counts are drawn on the window so you can see whether the three are staying even.

**If the window shows your own face**, it grabbed the laptop's built-in camera instead of the USB
one. Quit and add `--camera 1` (then `2`, if 1 is not it either).

**Why you label as you shoot.** You are already looking at the egg through the candler, so that is
the moment you know what it is. Taking 200 unlabelled photos and sorting them afterwards means
deciding all over again from a screen, which is slower and gets more of them wrong.

**The `--tag` is not optional and not cosmetic.** It goes into every filename, like
`good_jasfer_20260813_232041.jpg`. It is what stops two people's batches overwriting each other when
they get merged. Use the same tag every time.

⚠️ **Send a small first batch — 10 to 15 photos — and wait for it to be checked** before you shoot
hundreds. Focus, framing and candler position are cheap to fix after fifteen photos and expensive
after three hundred. Nobody has yet confirmed the webcam can even focus at candling distance.

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
{"image": "egg_0042.jpg", "class": "defective", "confidence": 0.91,
 "model_name": "candling-classifier", "model_version": "0.3.0+20260813T144500Z",
 "inference_time_ms": 105}
```

The last three fields describe *which* model answered. They are written by the training run, so they
cannot drift from the weights that produced the result.

---

## 7. Two things to watch out for

**Confidence is not accuracy.** The `confidence` number above is only how sure the model is about that one photo. It is not a score for the model. A model can be confidently wrong.

**Do not report the training score as the system's accuracy.** The number the training run prints is measured on photos it already learned from, so it is always flattering. The paper claims 85% accuracy, and that figure has to come from photos the model has never seen. Send the images to M and let the scoring happen separately.

---

## 8. Sending the photos over

The photos are deliberately kept out of GitHub, so committing them will not work and is not a mistake you can make by accident. Zip the `ai/dataset` folder and send it, or share the folder, whichever is easier. Keep the three folders intact inside the zip.

If you find a public egg dataset online, send the link before using it. Most egg photo collections online are ordinary photos of the outside of eggs, and ours are candling photos with light shining through them. The two look nothing alike and mixing them in makes the model worse, so it needs a look first.
