// Copyright (C) 2022 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only


#ifndef SBK_QTGRAPHS_PYTHON_H
#define SBK_QTGRAPHS_PYTHON_H

#include <sbkpython.h>
#include <sbkmodule.h>
#include <sbkconverter.h>
// Module Includes
#include <pyside6_qtquickwidgets_python.h>
#include <pyside6_qtcore_python.h>
#include <pyside6_qtgui_python.h>
#include <pyside6_qtquick_python.h>
#include <pyside6_qtnetwork_python.h>
#include <pyside6_qtopengl_python.h>
#include <pyside6_qtqml_python.h>
#include <pyside6_qtwidgets_python.h>

// Bound library includes
#include <QtGraphs/q3dscene.h>
#include <QtGraphs/q3dtheme.h>
#include <QtGraphs/qabstract3daxis.h>
#include <QtGraphs/qabstract3dgraph.h>
#include <QtGraphs/qabstract3dinputhandler.h>
#include <QtGraphs/qabstract3dseries.h>
#include <QtGraphs/qabstractaxis.h>
#include <QtGraphs/qabstractbarseries.h>
#include <QtGraphs/qabstractdataproxy.h>
#include <QtGraphs/qabstractseries.h>
#include <QtGraphs/qgraphtheme.h>
#include <QtGraphs/qitemmodelbardataproxy.h>
#include <QtGraphs/qitemmodelsurfacedataproxy.h>
#include <QtGraphs/qseriestheme.h>
#include <QtGraphs/qsurface3dseries.h>

QT_BEGIN_NAMESPACE
class Q3DBars;
class Q3DInputHandler;
class Q3DScatter;
class Q3DSurface;
class QBar3DSeries;
class QBarCategoryAxis;
class QBarDataItem;
class QBarDataProxy;
class QBarSeries;
class QBarSet;
class QCategory3DAxis;
class QCustom3DItem;
class QCustom3DLabel;
class QCustom3DVolume;
class QHeightMapSurfaceDataProxy;
class QItemModelScatterDataProxy;
class QLineSeries;
class QLogValue3DAxisFormatter;
class QScatter3DSeries;
class QScatterDataItem;
class QScatterDataProxy;
class QScatterSeries;
class QSurfaceDataItem;
class QSurfaceDataProxy;
class QTouch3DInputHandler;
class QValue3DAxis;
class QValue3DAxisFormatter;
class QValueAxis;
class QXYSeries;
QT_END_NAMESPACE

// Type indices
enum [[deprecated]] : int {
    SBK_Q3DBARS_IDX                                          = 0,
    SBK_Q3DINPUTHANDLER_IDX                                  = 2,
    SBK_Q3DSCATTER_IDX                                       = 4,
    SBK_Q3DSCENE_IDX                                         = 6,
    SBK_Q3DSURFACE_IDX                                       = 8,
    SBK_Q3DTHEME_COLORSTYLE_IDX                              = 12,
    SBK_Q3DTHEME_THEME_IDX                                   = 14,
    SBK_Q3DTHEME_IDX                                         = 10,
    SBK_QABSTRACT3DAXIS_AXISORIENTATION_IDX                  = 18,
    SBK_QABSTRACT3DAXIS_AXISTYPE_IDX                         = 20,
    SBK_QABSTRACT3DAXIS_IDX                                  = 16,
    SBK_QABSTRACT3DGRAPH_SELECTIONFLAG_IDX                   = 32,
    SBK_QFLAGS_QABSTRACT3DGRAPH_SELECTIONFLAG_IDX            = 84,
    SBK_QABSTRACT3DGRAPH_SHADOWQUALITY_IDX                   = 34,
    SBK_QABSTRACT3DGRAPH_ELEMENTTYPE_IDX                     = 26,
    SBK_QABSTRACT3DGRAPH_OPTIMIZATIONHINT_IDX                = 28,
    SBK_QFLAGS_QABSTRACT3DGRAPH_OPTIMIZATIONHINT_IDX         = 82,
    SBK_QABSTRACT3DGRAPH_RENDERINGMODE_IDX                   = 30,
    SBK_QABSTRACT3DGRAPH_CAMERAPRESET_IDX                    = 24,
    SBK_QABSTRACT3DGRAPH_IDX                                 = 22,
    SBK_QABSTRACT3DINPUTHANDLER_INPUTVIEW_IDX                = 38,
    SBK_QABSTRACT3DINPUTHANDLER_IDX                          = 36,
    SBK_QABSTRACT3DSERIES_SERIESTYPE_IDX                     = 44,
    SBK_QABSTRACT3DSERIES_MESH_IDX                           = 42,
    SBK_QABSTRACT3DSERIES_IDX                                = 40,
    SBK_QABSTRACTAXIS_AXISTYPE_IDX                           = 48,
    SBK_QABSTRACTAXIS_IDX                                    = 46,
    SBK_QABSTRACTBARSERIES_LABELSPOSITION_IDX                = 52,
    SBK_QABSTRACTBARSERIES_IDX                               = 50,
    SBK_QABSTRACTDATAPROXY_DATATYPE_IDX                      = 56,
    SBK_QABSTRACTDATAPROXY_IDX                               = 54,
    SBK_QABSTRACTSERIES_SERIESTYPE_IDX                       = 60,
    SBK_QABSTRACTSERIES_IDX                                  = 58,
    SBK_QBAR3DSERIES_IDX                                     = 62,
    SBK_QBARCATEGORYAXIS_IDX                                 = 64,
    SBK_QBARDATAITEM_IDX                                     = 66,
    SBK_QBARDATAPROXY_IDX                                    = 68,
    SBK_QBARSERIES_IDX                                       = 70,
    SBK_QBARSET_IDX                                          = 72,
    SBK_QCATEGORY3DAXIS_IDX                                  = 74,
    SBK_QCUSTOM3DITEM_IDX                                    = 76,
    SBK_QCUSTOM3DLABEL_IDX                                   = 78,
    SBK_QCUSTOM3DVOLUME_IDX                                  = 80,
    SBK_QGRAPHTHEME_COLORTHEME_IDX                           = 90,
    SBK_QGRAPHTHEME_IDX                                      = 88,
    SBK_QHEIGHTMAPSURFACEDATAPROXY_IDX                       = 92,
    SBK_QITEMMODELBARDATAPROXY_MULTIMATCHBEHAVIOR_IDX        = 96,
    SBK_QITEMMODELBARDATAPROXY_IDX                           = 94,
    SBK_QITEMMODELSCATTERDATAPROXY_IDX                       = 98,
    SBK_QITEMMODELSURFACEDATAPROXY_MULTIMATCHBEHAVIOR_IDX    = 102,
    SBK_QITEMMODELSURFACEDATAPROXY_IDX                       = 100,
    SBK_QLINESERIES_IDX                                      = 104,
    SBK_QLOGVALUE3DAXISFORMATTER_IDX                         = 106,
    SBK_QSCATTER3DSERIES_IDX                                 = 108,
    SBK_QSCATTERDATAITEM_IDX                                 = 110,
    SBK_QSCATTERDATAPROXY_IDX                                = 112,
    SBK_QSCATTERSERIES_IDX                                   = 114,
    SBK_QSERIESTHEME_SERIESCOLORTHEME_IDX                    = 118,
    SBK_QSERIESTHEME_IDX                                     = 116,
    SBK_QSURFACE3DSERIES_DRAWFLAG_IDX                        = 122,
    SBK_QFLAGS_QSURFACE3DSERIES_DRAWFLAG_IDX                 = 86,
    SBK_QSURFACE3DSERIES_IDX                                 = 120,
    SBK_QSURFACEDATAITEM_IDX                                 = 124,
    SBK_QSURFACEDATAPROXY_IDX                                = 126,
    SBK_QTOUCH3DINPUTHANDLER_IDX                             = 128,
    SBK_QVALUE3DAXIS_IDX                                     = 130,
    SBK_QVALUE3DAXISFORMATTER_IDX                            = 132,
    SBK_QVALUEAXIS_IDX                                       = 134,
    SBK_QXYSERIES_IDX                                        = 136,
    SBK_QTGRAPHS_IDX_COUNT                                   = 138,
};

// Type indices
enum : int {
    SBK_Q3DBars_IDX                                          = 0,
    SBK_Q3DInputHandler_IDX                                  = 1,
    SBK_Q3DScatter_IDX                                       = 2,
    SBK_Q3DScene_IDX                                         = 3,
    SBK_Q3DSurface_IDX                                       = 4,
    SBK_Q3DTheme_ColorStyle_IDX                              = 6,
    SBK_Q3DTheme_Theme_IDX                                   = 7,
    SBK_Q3DTheme_IDX                                         = 5,
    SBK_QAbstract3DAxis_AxisOrientation_IDX                  = 9,
    SBK_QAbstract3DAxis_AxisType_IDX                         = 10,
    SBK_QAbstract3DAxis_IDX                                  = 8,
    SBK_QAbstract3DGraph_SelectionFlag_IDX                   = 16,
    SBK_QFlags_QAbstract3DGraph_SelectionFlag_IDX            = 42,
    SBK_QAbstract3DGraph_ShadowQuality_IDX                   = 17,
    SBK_QAbstract3DGraph_ElementType_IDX                     = 13,
    SBK_QAbstract3DGraph_OptimizationHint_IDX                = 14,
    SBK_QFlags_QAbstract3DGraph_OptimizationHint_IDX         = 41,
    SBK_QAbstract3DGraph_RenderingMode_IDX                   = 15,
    SBK_QAbstract3DGraph_CameraPreset_IDX                    = 12,
    SBK_QAbstract3DGraph_IDX                                 = 11,
    SBK_QAbstract3DInputHandler_InputView_IDX                = 19,
    SBK_QAbstract3DInputHandler_IDX                          = 18,
    SBK_QAbstract3DSeries_SeriesType_IDX                     = 22,
    SBK_QAbstract3DSeries_Mesh_IDX                           = 21,
    SBK_QAbstract3DSeries_IDX                                = 20,
    SBK_QAbstractAxis_AxisType_IDX                           = 24,
    SBK_QAbstractAxis_IDX                                    = 23,
    SBK_QAbstractBarSeries_LabelsPosition_IDX                = 26,
    SBK_QAbstractBarSeries_IDX                               = 25,
    SBK_QAbstractDataProxy_DataType_IDX                      = 28,
    SBK_QAbstractDataProxy_IDX                               = 27,
    SBK_QAbstractSeries_SeriesType_IDX                       = 30,
    SBK_QAbstractSeries_IDX                                  = 29,
    SBK_QBar3DSeries_IDX                                     = 31,
    SBK_QBarCategoryAxis_IDX                                 = 32,
    SBK_QBarDataItem_IDX                                     = 33,
    SBK_QBarDataProxy_IDX                                    = 34,
    SBK_QBarSeries_IDX                                       = 35,
    SBK_QBarSet_IDX                                          = 36,
    SBK_QCategory3DAxis_IDX                                  = 37,
    SBK_QCustom3DItem_IDX                                    = 38,
    SBK_QCustom3DLabel_IDX                                   = 39,
    SBK_QCustom3DVolume_IDX                                  = 40,
    SBK_QGraphTheme_ColorTheme_IDX                           = 45,
    SBK_QGraphTheme_IDX                                      = 44,
    SBK_QHeightMapSurfaceDataProxy_IDX                       = 46,
    SBK_QItemModelBarDataProxy_MultiMatchBehavior_IDX        = 48,
    SBK_QItemModelBarDataProxy_IDX                           = 47,
    SBK_QItemModelScatterDataProxy_IDX                       = 49,
    SBK_QItemModelSurfaceDataProxy_MultiMatchBehavior_IDX    = 51,
    SBK_QItemModelSurfaceDataProxy_IDX                       = 50,
    SBK_QLineSeries_IDX                                      = 52,
    SBK_QLogValue3DAxisFormatter_IDX                         = 53,
    SBK_QScatter3DSeries_IDX                                 = 54,
    SBK_QScatterDataItem_IDX                                 = 55,
    SBK_QScatterDataProxy_IDX                                = 56,
    SBK_QScatterSeries_IDX                                   = 57,
    SBK_QSeriesTheme_SeriesColorTheme_IDX                    = 59,
    SBK_QSeriesTheme_IDX                                     = 58,
    SBK_QSurface3DSeries_DrawFlag_IDX                        = 61,
    SBK_QFlags_QSurface3DSeries_DrawFlag_IDX                 = 43,
    SBK_QSurface3DSeries_IDX                                 = 60,
    SBK_QSurfaceDataItem_IDX                                 = 62,
    SBK_QSurfaceDataProxy_IDX                                = 63,
    SBK_QTouch3DInputHandler_IDX                             = 64,
    SBK_QValue3DAxis_IDX                                     = 65,
    SBK_QValue3DAxisFormatter_IDX                            = 66,
    SBK_QValueAxis_IDX                                       = 67,
    SBK_QXYSeries_IDX                                        = 68,
    SBK_QtGraphs_IDX_COUNT                                   = 69,
};

// This variable stores all Python types exported by this module.
extern Shiboken::Module::TypeInitStruct *SbkPySide6_QtGraphsTypeStructs;

// This variable stores all Python types exported by this module in a backwards compatible way with identical indexing.
[[deprecated]] extern PyTypeObject **SbkPySide6_QtGraphsTypes;

// This variable stores the Python module object exported by this module.
extern PyObject *SbkPySide6_QtGraphsModuleObject;

// This variable stores all type converters exported by this module.
extern SbkConverter **SbkPySide6_QtGraphsTypeConverters;

// Converter indices
enum [[deprecated]] : int {
    SBK_QTGRAPHS_QLIST_INT_IDX                               = 0, // QList<int>
    SBK_QTGRAPHS_QLIST_QCUSTOM3DITEMPTR_IDX                  = 2, // QList<QCustom3DItem*>
    SBK_QTGRAPHS_QLIST_QQMLERROR_IDX                         = 4, // QList<QQmlError>
    SBK_QTGRAPHS_QLIST_QABSTRACT3DINPUTHANDLERPTR_IDX        = 6, // QList<QAbstract3DInputHandler*>
    SBK_QTGRAPHS_QLIST_Q3DTHEMEPTR_IDX                       = 8, // QList<Q3DTheme*>
    SBK_QTGRAPHS_QLIST_QVALUE3DAXISPTR_IDX                   = 10, // QList<QValue3DAxis*>
    SBK_QTGRAPHS_QLIST_QSURFACE3DSERIESPTR_IDX               = 12, // QList<QSurface3DSeries*>
    SBK_QTGRAPHS_QLIST_QSCATTER3DSERIESPTR_IDX               = 14, // QList<QScatter3DSeries*>
    SBK_QTGRAPHS_QLIST_QABSTRACT3DAXISPTR_IDX                = 16, // QList<QAbstract3DAxis*>
    SBK_QTGRAPHS_QLIST_QBAR3DSERIESPTR_IDX                   = 18, // QList<QBar3DSeries*>
    SBK_QTGRAPHS_QLIST_QOBJECTPTR_IDX                        = 20, // QList<QObject*>
    SBK_QTGRAPHS_QLIST_QBYTEARRAY_IDX                        = 22, // QList<QByteArray>
    SBK_QTGRAPHS_QLIST_FLOAT_IDX                             = 24, // QList<float>
    SBK_QTGRAPHS_QLIST_QCOLOR_IDX                            = 26, // QList<QColor>
    SBK_QTGRAPHS_QLIST_UCHAR_IDX                             = 28, // QList<uchar>
    SBK_QTGRAPHS_QLIST_UNSIGNEDINT_IDX                       = 30, // QList<unsigned int>
    SBK_QTGRAPHS_QLIST_QIMAGEPTR_IDX                         = 32, // QList<QImage*>
    SBK_QTGRAPHS_QLIST_QREAL_IDX                             = 34, // QList<qreal>
    SBK_QTGRAPHS_QLIST_QVARIANT_IDX                          = 36, // QList<QVariant>
    SBK_QTGRAPHS_QLIST_QABSTRACTAXISPTR_IDX                  = 38, // QList<QAbstractAxis*>
    SBK_QTGRAPHS_QLIST_QPOINTF_IDX                           = 40, // QList<QPointF>
    SBK_QTGRAPHS_QLIST_QBARSETPTR_IDX                        = 42, // QList<QBarSet*>
    SBK_QTGRAPHS_QLIST_QSURFACEDATAITEM_IDX                  = 44, // QList<QSurfaceDataItem>
    SBK_QTGRAPHS_QLIST_QLIST_QSURFACEDATAITEM_IDX            = 46, // QList<QList< QSurfaceDataItem>>
    SBK_QTGRAPHS_QLIST_QSCATTERDATAITEM_IDX                  = 48, // QList<QScatterDataItem>
    SBK_QTGRAPHS_QLIST_QBARDATAITEM_IDX                      = 50, // QList<QBarDataItem>
    SBK_QTGRAPHS_QLIST_QLIST_QBARDATAITEM_IDX                = 52, // QList<QList< QBarDataItem>>
    SBK_QTGRAPHS_QLIST_QLINEARGRADIENT_IDX                   = 54, // QList<QLinearGradient>
    SBK_QTGRAPHS_QLIST_QSTRING_IDX                           = 56, // QList<QString>
    SBK_QTGRAPHS_QMAP_QSTRING_QVARIANT_IDX                   = 58, // QMap<QString,QVariant>
    SBK_QTGRAPHS_CONVERTERS_IDX_COUNT                        = 60,
};

// Converter indices
enum : int {
    SBK_QtGraphs_QList_int_IDX                               = 0, // QList<int>
    SBK_QtGraphs_QList_QCustom3DItemPTR_IDX                  = 1, // QList<QCustom3DItem*>
    SBK_QtGraphs_QList_QQmlError_IDX                         = 2, // QList<QQmlError>
    SBK_QtGraphs_QList_QAbstract3DInputHandlerPTR_IDX        = 3, // QList<QAbstract3DInputHandler*>
    SBK_QtGraphs_QList_Q3DThemePTR_IDX                       = 4, // QList<Q3DTheme*>
    SBK_QtGraphs_QList_QValue3DAxisPTR_IDX                   = 5, // QList<QValue3DAxis*>
    SBK_QtGraphs_QList_QSurface3DSeriesPTR_IDX               = 6, // QList<QSurface3DSeries*>
    SBK_QtGraphs_QList_QScatter3DSeriesPTR_IDX               = 7, // QList<QScatter3DSeries*>
    SBK_QtGraphs_QList_QAbstract3DAxisPTR_IDX                = 8, // QList<QAbstract3DAxis*>
    SBK_QtGraphs_QList_QBar3DSeriesPTR_IDX                   = 9, // QList<QBar3DSeries*>
    SBK_QtGraphs_QList_QObjectPTR_IDX                        = 10, // QList<QObject*>
    SBK_QtGraphs_QList_QByteArray_IDX                        = 11, // QList<QByteArray>
    SBK_QtGraphs_QList_float_IDX                             = 12, // QList<float>
    SBK_QtGraphs_QList_QColor_IDX                            = 13, // QList<QColor>
    SBK_QtGraphs_QList_uchar_IDX                             = 14, // QList<uchar>
    SBK_QtGraphs_QList_unsignedint_IDX                       = 15, // QList<unsigned int>
    SBK_QtGraphs_QList_QImagePTR_IDX                         = 16, // QList<QImage*>
    SBK_QtGraphs_QList_qreal_IDX                             = 17, // QList<qreal>
    SBK_QtGraphs_QList_QVariant_IDX                          = 18, // QList<QVariant>
    SBK_QtGraphs_QList_QAbstractAxisPTR_IDX                  = 19, // QList<QAbstractAxis*>
    SBK_QtGraphs_QList_QPointF_IDX                           = 20, // QList<QPointF>
    SBK_QtGraphs_QList_QBarSetPTR_IDX                        = 21, // QList<QBarSet*>
    SBK_QtGraphs_QList_QSurfaceDataItem_IDX                  = 22, // QList<QSurfaceDataItem>
    SBK_QtGraphs_QList_QList_QSurfaceDataItem_IDX            = 23, // QList<QList< QSurfaceDataItem>>
    SBK_QtGraphs_QList_QScatterDataItem_IDX                  = 24, // QList<QScatterDataItem>
    SBK_QtGraphs_QList_QBarDataItem_IDX                      = 25, // QList<QBarDataItem>
    SBK_QtGraphs_QList_QList_QBarDataItem_IDX                = 26, // QList<QList< QBarDataItem>>
    SBK_QtGraphs_QList_QLinearGradient_IDX                   = 27, // QList<QLinearGradient>
    SBK_QtGraphs_QList_QString_IDX                           = 28, // QList<QString>
    SBK_QtGraphs_QMap_QString_QVariant_IDX                   = 29, // QMap<QString,QVariant>
    SBK_QtGraphs_CONVERTERS_IDX_COUNT                        = 30,
};
// Macros for type check

QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject *SbkType< ::Q3DBars >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_Q3DBars_IDX]); }
template<> inline PyTypeObject *SbkType< ::Q3DInputHandler >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_Q3DInputHandler_IDX]); }
template<> inline PyTypeObject *SbkType< ::Q3DScatter >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_Q3DScatter_IDX]); }
template<> inline PyTypeObject *SbkType< ::Q3DScene >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_Q3DScene_IDX]); }
template<> inline PyTypeObject *SbkType< ::Q3DSurface >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_Q3DSurface_IDX]); }
template<> inline PyTypeObject *SbkType< ::Q3DTheme::ColorStyle >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_Q3DTheme_ColorStyle_IDX]); }
template<> inline PyTypeObject *SbkType< ::Q3DTheme::Theme >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_Q3DTheme_Theme_IDX]); }
template<> inline PyTypeObject *SbkType< ::Q3DTheme >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_Q3DTheme_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DAxis::AxisOrientation >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DAxis_AxisOrientation_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DAxis::AxisType >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DAxis_AxisType_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DAxis >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DAxis_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DGraph::SelectionFlag >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DGraph_SelectionFlag_IDX]); }
template<> inline PyTypeObject *SbkType< ::QFlags<QAbstract3DGraph::SelectionFlag> >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QFlags_QAbstract3DGraph_SelectionFlag_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DGraph::ShadowQuality >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DGraph_ShadowQuality_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DGraph::ElementType >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DGraph_ElementType_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DGraph::OptimizationHint >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DGraph_OptimizationHint_IDX]); }
template<> inline PyTypeObject *SbkType< ::QFlags<QAbstract3DGraph::OptimizationHint> >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QFlags_QAbstract3DGraph_OptimizationHint_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DGraph::RenderingMode >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DGraph_RenderingMode_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DGraph::CameraPreset >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DGraph_CameraPreset_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DGraph >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DGraph_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DInputHandler::InputView >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DInputHandler_InputView_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DInputHandler >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DInputHandler_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DSeries::SeriesType >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DSeries_SeriesType_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DSeries::Mesh >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DSeries_Mesh_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstract3DSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstract3DSeries_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstractAxis::AxisType >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstractAxis_AxisType_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstractAxis >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstractAxis_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstractBarSeries::LabelsPosition >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstractBarSeries_LabelsPosition_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstractBarSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstractBarSeries_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstractDataProxy::DataType >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstractDataProxy_DataType_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstractDataProxy >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstractDataProxy_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstractSeries::SeriesType >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstractSeries_SeriesType_IDX]); }
template<> inline PyTypeObject *SbkType< ::QAbstractSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QAbstractSeries_IDX]); }
template<> inline PyTypeObject *SbkType< ::QBar3DSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QBar3DSeries_IDX]); }
template<> inline PyTypeObject *SbkType< ::QBarCategoryAxis >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QBarCategoryAxis_IDX]); }
template<> inline PyTypeObject *SbkType< ::QBarDataItem >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QBarDataItem_IDX]); }
template<> inline PyTypeObject *SbkType< ::QBarDataProxy >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QBarDataProxy_IDX]); }
template<> inline PyTypeObject *SbkType< ::QBarSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QBarSeries_IDX]); }
template<> inline PyTypeObject *SbkType< ::QBarSet >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QBarSet_IDX]); }
template<> inline PyTypeObject *SbkType< ::QCategory3DAxis >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QCategory3DAxis_IDX]); }
template<> inline PyTypeObject *SbkType< ::QCustom3DItem >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QCustom3DItem_IDX]); }
template<> inline PyTypeObject *SbkType< ::QCustom3DLabel >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QCustom3DLabel_IDX]); }
template<> inline PyTypeObject *SbkType< ::QCustom3DVolume >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QCustom3DVolume_IDX]); }
template<> inline PyTypeObject *SbkType< ::QGraphTheme::ColorTheme >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QGraphTheme_ColorTheme_IDX]); }
template<> inline PyTypeObject *SbkType< ::QGraphTheme >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QGraphTheme_IDX]); }
template<> inline PyTypeObject *SbkType< ::QHeightMapSurfaceDataProxy >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QHeightMapSurfaceDataProxy_IDX]); }
template<> inline PyTypeObject *SbkType< ::QItemModelBarDataProxy::MultiMatchBehavior >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QItemModelBarDataProxy_MultiMatchBehavior_IDX]); }
template<> inline PyTypeObject *SbkType< ::QItemModelBarDataProxy >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QItemModelBarDataProxy_IDX]); }
template<> inline PyTypeObject *SbkType< ::QItemModelScatterDataProxy >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QItemModelScatterDataProxy_IDX]); }
template<> inline PyTypeObject *SbkType< ::QItemModelSurfaceDataProxy::MultiMatchBehavior >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QItemModelSurfaceDataProxy_MultiMatchBehavior_IDX]); }
template<> inline PyTypeObject *SbkType< ::QItemModelSurfaceDataProxy >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QItemModelSurfaceDataProxy_IDX]); }
template<> inline PyTypeObject *SbkType< ::QLineSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QLineSeries_IDX]); }
template<> inline PyTypeObject *SbkType< ::QLogValue3DAxisFormatter >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QLogValue3DAxisFormatter_IDX]); }
template<> inline PyTypeObject *SbkType< ::QScatter3DSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QScatter3DSeries_IDX]); }
template<> inline PyTypeObject *SbkType< ::QScatterDataItem >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QScatterDataItem_IDX]); }
template<> inline PyTypeObject *SbkType< ::QScatterDataProxy >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QScatterDataProxy_IDX]); }
template<> inline PyTypeObject *SbkType< ::QScatterSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QScatterSeries_IDX]); }
template<> inline PyTypeObject *SbkType< ::QSeriesTheme::SeriesColorTheme >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QSeriesTheme_SeriesColorTheme_IDX]); }
template<> inline PyTypeObject *SbkType< ::QSeriesTheme >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QSeriesTheme_IDX]); }
template<> inline PyTypeObject *SbkType< ::QSurface3DSeries::DrawFlag >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QSurface3DSeries_DrawFlag_IDX]); }
template<> inline PyTypeObject *SbkType< ::QFlags<QSurface3DSeries::DrawFlag> >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QFlags_QSurface3DSeries_DrawFlag_IDX]); }
template<> inline PyTypeObject *SbkType< ::QSurface3DSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QSurface3DSeries_IDX]); }
template<> inline PyTypeObject *SbkType< ::QSurfaceDataItem >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QSurfaceDataItem_IDX]); }
template<> inline PyTypeObject *SbkType< ::QSurfaceDataProxy >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QSurfaceDataProxy_IDX]); }
template<> inline PyTypeObject *SbkType< ::QTouch3DInputHandler >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QTouch3DInputHandler_IDX]); }
template<> inline PyTypeObject *SbkType< ::QValue3DAxis >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QValue3DAxis_IDX]); }
template<> inline PyTypeObject *SbkType< ::QValue3DAxisFormatter >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QValue3DAxisFormatter_IDX]); }
template<> inline PyTypeObject *SbkType< ::QValueAxis >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QValueAxis_IDX]); }
template<> inline PyTypeObject *SbkType< ::QXYSeries >() { return Shiboken::Module::get(SbkPySide6_QtGraphsTypeStructs[SBK_QXYSeries_IDX]); }

} // namespace Shiboken

QT_WARNING_POP
#endif // SBK_QTGRAPHS_PYTHON_H

