"""
Usage:
    python assignment1_question2.py

"""

import sys
import os
import vtk


def find_dataset(filename):
    # Locate the dataset file in the expected paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, filename),
        os.path.join(script_dir, "Data", filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def setup_color_transfer_function():
    # Map data values to RGB colours with linear interpolation between control points
    ctf = vtk.vtkColorTransferFunction()
    ctf.AddRGBPoint(-4931.54,  0.0, 1.0, 1.0)
    ctf.AddRGBPoint(-2508.95,  0.0, 0.0, 1.0)
    ctf.AddRGBPoint(-1873.9,   0.0, 0.0, 0.5)
    ctf.AddRGBPoint(-1027.16,  1.0, 0.0, 0.0)
    ctf.AddRGBPoint( -298.031, 1.0, 0.4, 0.0)
    ctf.AddRGBPoint(  2594.97, 1.0, 1.0, 0.0)
    return ctf


def setup_opacity_transfer_function():
    # Piecewise-linear opacity: fully opaque at low values, transparent at high values
    otf = vtk.vtkPiecewiseFunction()
    otf.AddPoint(-4931.54, 1.0)
    otf.AddPoint(  101.815, 0.002)
    otf.AddPoint( 2594.97, 0.0)
    return otf


def volume_render(input_file, use_phong):

    # Read the 3D VTKImageData (.vti) file
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(input_file)
    reader.Update()
    image_data = reader.GetOutput()

    # Build the colour and opacity transfer functions
    color_tf   = setup_color_transfer_function()
    opacity_tf = setup_opacity_transfer_function()

    # Bind transfer functions to the volume property
    volume_property = vtk.vtkVolumeProperty()
    volume_property.SetColor(color_tf)
    volume_property.SetScalarOpacity(opacity_tf)
    volume_property.SetInterpolationTypeToLinear()   # trilinear interpolation inside voxels

    if use_phong:
        # Enable Phong shading with equal ambient/diffuse/specular contributions
        volume_property.ShadeOn()
        volume_property.SetAmbient(0.5)
        volume_property.SetDiffuse(0.5)
        volume_property.SetSpecular(0.5)
    else:
        volume_property.ShadeOff()

    # Smart volume mapper automatically selects GPU ray-casting when available
    mapper = vtk.vtkSmartVolumeMapper()
    mapper.SetInputData(image_data)

    # Attach the mapper and property to the volume actor
    volume = vtk.vtkVolume()
    volume.SetMapper(mapper)
    volume.SetProperty(volume_property)

    # Bounding-box outline to provide spatial context in the scene
    outline_filter = vtk.vtkOutlineFilter()
    outline_filter.SetInputData(image_data)
    outline_mapper = vtk.vtkPolyDataMapper()
    outline_mapper.SetInputConnection(outline_filter.GetOutputPort())
    outline_actor = vtk.vtkActor()
    outline_actor.SetMapper(outline_mapper)
    outline_actor.GetProperty().SetColor(1.0, 1.0, 1.0)   # white outline

    # On-screen HUD showing current shading mode
    label = vtk.vtkTextActor()
    label.SetInput("Phong Shading: ON" if use_phong else "Phong Shading: OFF")
    label.GetTextProperty().SetFontSize(22)
    label.GetTextProperty().SetColor(1.0, 1.0, 0.0)
    label.SetPosition(10, 10)

    # Set up the renderer with all scene elements
    renderer = vtk.vtkRenderer()
    renderer.AddVolume(volume)
    renderer.AddActor(outline_actor)
    renderer.AddViewProp(label)   # AddViewProp is the non-deprecated replacement for AddActor2D
    renderer.SetBackground(0.08, 0.08, 0.08)
    renderer.ResetCamera()

    # Create a 1000x1000 render window
    window = vtk.vtkRenderWindow()
    window.AddRenderer(renderer)
    window.SetSize(1000, 1000)
    window.SetWindowName(
        f"Volume Rendering  |  {'With' if use_phong else 'Without'} Phong Shading"
    )

    # Launch the interactive window; mouse controls rotate/zoom/pan
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(window)
    window.Render()
    interactor.Start()


if __name__ == "__main__":

    # Locate the dataset file in the expected paths
    dataset_file = find_dataset("Isabel_3D.vti")
    if not dataset_file:
        path = input("\nIsabel_3D.vti not found. Enter full path: ").strip().strip('"').strip("'")
        dataset_file = os.path.abspath(path)
        if not os.path.isfile(dataset_file):
            sys.exit(1)

    # Prompt the user to enable or disable Phong shading
    while True:
        raw = input("\nEnable Phong shading? (y/n): ").strip().lower()
        if raw in ("y", "yes"):
            use_phong = True
            break
        elif raw in ("n", "no"):
            use_phong = False
            break

    # Run the volume renderer
    volume_render(dataset_file, use_phong)